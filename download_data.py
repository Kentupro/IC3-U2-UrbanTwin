"""Download the exact published MOLI-SOL archive and verify it before use."""
import hashlib
from pathlib import Path
import urllib.request

from pipeline import EXPECTED_MD5

URL = 'https://zenodo.org/records/17044034/files/moli-sol-dataset.zip?download=1'
DESTINATION = Path(__file__).resolve().parent / 'data/raw/moli-sol-dataset.zip'


def main():
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        if hashlib.md5(DESTINATION.read_bytes()).hexdigest() != EXPECTED_MD5:
            raise ValueError('Existing archive has an unexpected checksum; review it manually.')
        print('Archive already present and verified:', DESTINATION)
        return
    temporary = DESTINATION.with_suffix('.zip.part')
    try:
        request = urllib.request.Request(URL, headers={'User-Agent': 'IC3-U2-UrbanTwin/CP2'})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as target:
            while block := response.read(1024 * 1024):
                target.write(block)
        if hashlib.md5(temporary.read_bytes()).hexdigest() != EXPECTED_MD5:
            raise ValueError('Downloaded archive checksum does not match Zenodo v1.0.0.')
        temporary.replace(DESTINATION)
    finally:
        temporary.unlink(missing_ok=True)
    print('Archive downloaded and verified:', DESTINATION)


if __name__ == '__main__':
    main()
