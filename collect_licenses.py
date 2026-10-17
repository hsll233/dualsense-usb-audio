"""Copy installed runtime notices alongside the portable distribution."""
import importlib.metadata
import shutil
import sys
from pathlib import Path


def collect(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    notices = ["Third-party components bundled in DualSense USB Audio", "",
               "See licenses/ for full license texts. No licenses are replaced by this index.", ""]
    for name in ("numpy", "sounddevice", "PyAudioWPatch", "hidapi", "cffi", "pycparser", "pyinstaller"):
        distribution = importlib.metadata.distribution(name)
        count = 0
        for entry in distribution.files or []:
            if not any(part.lower().startswith(("license", "copying", "notice")) for part in entry.parts):
                continue
            source = Path(distribution.locate_file(entry))
            if not source.is_file():
                continue
            target = root / name / Path(*entry.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            count += 1
        if not count:
            raise RuntimeError(f"Missing license texts for {name}")
        notices.append(f"{name} {distribution.version}: licenses/{name}/")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    shutil.copyfile(python_license, root / "Python-LICENSE.txt")
    notices.extend([f"Python {sys.version.split()[0]}: licenses/Python-LICENSE.txt", "",
                    "PortAudio is bundled by PyAudioWPatch and python-sounddevice.",
                    "Its notice is reproduced in licenses/PortAudio-LICENSE.txt.",
                    "PyInstaller is a build tool; its bootloader has a distribution exception."])
    (root.parent / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(notices) + "\n", encoding="utf-8")


if __name__ == "__main__":
    collect(sys.argv[1])
