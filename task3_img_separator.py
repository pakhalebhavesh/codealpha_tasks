from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
from typing import List, Optional, Set, Tuple
import unittest
from unittest.mock import patch
import uuid

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ImageOrganizer")


@dataclass(frozen=True)
class MoveResult:
    """Immutable record of an individual file transfer operation."""
    source_path: Path
    destination_path: Path
    success: bool
    error_message: Optional[str] = None


class ImageOrganizer:
    """
    Scans, validates, and safely moves image files to a dedicated target directory.
    Features non-destructive collision resolution and path safety checks.
    """

    SUPPORTED_EXTENSIONS: Set[str] = {".jpg", ".jpeg"}

    def __init__(self, source_dir: Path, target_dirname: str = "Organized_Images"):
        self.source_dir = Path(source_dir).resolve()
        self.target_dir = (self.source_dir / target_dirname).resolve()

    def _resolve_collision(self, destination: Path) -> Path:
        """Appends a counter suffix if a target file already exists."""
        if not destination.exists():
            return destination

        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        counter = 1

        while destination.exists():
            destination = parent / f"{stem}_{counter}{suffix}"
            counter += 1

        return destination

    def discover_images(self) -> List[Path]:
        """Discovers all valid image files strictly within the source directory."""
        if not self.source_dir.is_dir():
            raise NotADirectoryError(f"Source directory does not exist: {self.source_dir}")

        images = [
            file
            for file in self.source_dir.iterdir()
            if file.is_file() and file.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]
        logger.info("Found %d target image(s) in %s", len(images), self.source_dir)
        return images

    def organize(self, dry_run: bool = False) -> Tuple[int, List[MoveResult]]:
        """
        Executes file migration with collision mitigation and error safety.
        Returns the count of successfully moved files and the full audit trail.
        """
        images = self.discover_images()
        if not images:
            logger.info("No matching image files found to organize.")
            return 0, []

        if not dry_run:
            self.target_dir.mkdir(parents=True, exist_ok=True)

        results: List[MoveResult] = []
        success_count = 0

        for file_path in images:
            target_dest = self.target_dir / file_path.name
            resolved_dest = self._resolve_collision(target_dest)

            if dry_run:
                logger.info("[DRY-RUN] Move %s -> %s", file_path.name, resolved_dest)
                results.append(MoveResult(file_path, resolved_dest, True))
                success_count += 1
                continue

            try:
                # shutil.move handles both same-device moves and cross-device migrations
                shutil.move(str(file_path), str(resolved_dest))
                logger.info("Moved: %s -> %s", file_path.name, resolved_dest.name)
                results.append(MoveResult(file_path, resolved_dest, True))
                success_count += 1
            except (OSError, PermissionError, shutil.Error) as err:
                logger.error("Failed to migrate %s: %s", file_path.name, err)
                results.append(MoveResult(file_path, resolved_dest, False, str(err)))

        logger.info(
            "Batch execution finished. Successfully migrated: %d/%d",
            success_count,
            len(images),
        )
        return success_count, results


# =====================================================================
# Automated Test Suite (Runs in isolated temp directory)
# =====================================================================
class TestImageOrganizer(unittest.TestCase):
    """Hermetic unit tests executing in ephemeral sandbox environments."""

    def setUp(self):
        self.test_root = Path(f"./temp_test_{uuid.uuid4().hex}").resolve()
        self.test_root.mkdir(parents=True, exist_ok=True)
        self.organizer = ImageOrganizer(self.test_root)

    def tearDown(self):
        """Cleanup test directories cleanly."""
        if self.test_root.exists():
            shutil.rmtree(self.test_root)

    def test_case_insensitive_jpg_detection(self):
        """Validates detection of .jpg, .JPG, and .jpeg extensions."""
        (self.test_root / "sample1.jpg").write_text("data")
        (self.test_root / "sample2.JPG").write_text("data")
        (self.test_root / "sample3.jpeg").write_text("data")
        (self.test_root / "ignore.png").write_text("data")
        (self.test_root / "ignore.txt").write_text("data")

        discovered = self.organizer.discover_images()
        discovered_names = {f.name for f in discovered}

        self.assertEqual(len(discovered), 3)
        self.assertIn("sample1.jpg", discovered_names)
        self.assertIn("sample2.JPG", discovered_names)
        self.assertIn("sample3.jpeg", discovered_names)

    def test_file_migration_and_collision_resolution(self):
        """Validates that duplicate filenames do not overwrite existing files."""
        # Create an existing target file
        target_dir = self.test_root / "Organized_Images"
        target_dir.mkdir(parents=True)
        (target_dir / "photo.jpg").write_text("original content")

        # Create a new file with the same name in the source directory
        (self.test_root / "photo.jpg").write_text("new content")

        successes, results = self.organizer.organize()

        self.assertEqual(successes, 1)
        self.assertTrue((target_dir / "photo.jpg").exists())
        self.assertTrue((target_dir / "photo_1.jpg").exists())
        self.assertEqual((target_dir / "photo.jpg").read_text(), "original content")
        self.assertEqual((target_dir / "photo_1.jpg").read_text(), "new content")

    def test_dry_run_mode(self):
        """Validates that dry run mode does not mutate disk state."""
        test_file = self.test_root / "dry_test.jpg"
        test_file.write_text("payload")

        successes, _ = self.organizer.organize(dry_run=True)

        self.assertEqual(successes, 1)
        self.assertTrue(test_file.exists())
        self.assertFalse((self.test_root / "Organized_Images").exists())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        unittest.main(argv=[sys.argv[0]])
    else:
        # Standard execution against the current working directory
        current_dir = Path.cwd()
        organizer = ImageOrganizer(current_dir)
        organizer.organize()