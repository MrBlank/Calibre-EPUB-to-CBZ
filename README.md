# EPUB to CBZ - Calibre Plugin

A Calibre plugin to convert EPUB files to CBZ (Comic Book ZIP) format. This plugin allows you to easily convert your EPUB comics and manga to CBZ format directly within Calibre.

## Installation

1. Open Calibre
2. Go to Preferences (⌘ + P on macOS)
3. Click on "Plugins" under "Advanced"
4. Click "Load plugin from file"
5. Select the `EPUBToCBZ.zip` plugin file included in this repository
6. Restart Calibre

## Usage

1. Select one or more EPUB books in your Calibre library
2. Right-click and select "Convert books" > "Convert individually" (or press ⌘ + E on macOS)
3. In the top-right corner, select "CBZ" as the output format
4. Click "OK" to start the conversion

The converted CBZ files will appear in your Calibre library alongside the original EPUB files.

## Notes

- The plugin preserves image quality during conversion
- Page ordering is maintained from the original EPUB
- Supports batch conversion of multiple books

## Output

Converted files will be saved in the `output` directory with the same name as the input file but with a `.cbz` extension.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
