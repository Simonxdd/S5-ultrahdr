import argparse
import sys
from pathlib import Path
from src.raw_processing import generate_ultra_hdr_avif, AVIFSize
from src.check_dependencies import check_dependencies

def valid_RW2(path_str):
    p = Path(path_str)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"Input file does not exist: {path_str}")
    if not p.is_file():
        raise argparse.ArgumentTypeError(f"Input path is not a file: {path_str}")
    if p.suffix.lower() != '.rw2':
        raise argparse.ArgumentTypeError(f"File must be a Lumix .RW2 raw file: {path_str}")
    return p

def valid_target_AVIF(path_str):
    p = Path(path_str)
    if not p.parent.exists():
        raise argparse.ArgumentTypeError(f"Target directory does not exist: {p.parent}")
    if p.suffix.lower() != '.avif':
        raise argparse.ArgumentTypeError(f"Output file must have a .avif extension: {path_str}")
    return p

def valid_avif_size(size_str):
    try:
        # Look up the enum member by name (case-insensitive)
        return AVIFSize[size_str.upper()]
    except KeyError:
        valid_names = [e.name for e in AVIFSize]
        raise argparse.ArgumentTypeError(
            f"Invalid size: '{size_str}'. Choose from: {', '.join(valid_names)}"
        )

def main():
    parser = argparse.ArgumentParser(description='Lumix S5 Ultra HDR image processor')
    parser.add_argument('-i', type=valid_RW2, required=True, help="Path to input file")
    parser.add_argument('-o', type=valid_target_AVIF, required=True, help="Path to output file")
    parser.add_argument('-size', type=valid_avif_size, default=AVIFSize.PLUS, help="Set AVIF size for decoding compatibility")
    if not check_dependencies("libavif"):
        sys.exit(0)
    args = parser.parse_args()
    generate_ultra_hdr_avif(args.i, args.o, args.size)

if __name__ == '__main__':
    main()