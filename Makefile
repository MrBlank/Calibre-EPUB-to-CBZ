# Calibre plugin build configuration
NAME := EPUBToCBZ
SRC := .
ZIP := $(NAME).zip
SRC_FILES := __init__.py

.PHONY: all zip install test clean

all: $(ZIP)

$(ZIP): $(addprefix $(SRC)/,$(SRC_FILES))
	zip -r $(ZIP) $(SRC_FILES)

zip: $(ZIP)

install: $(ZIP)
	/Applications/calibre.app/Contents/MacOS/calibre-customize -a $(ZIP)

test: install
	/Applications/calibre.app/Contents/MacOS/calibre-debug -e $(SRC)/__init__.py

clean:
	rm -f $(ZIP)

# Print help information
help:
	@echo "Available targets:"
	@echo "  all     - Build the plugin (default)"
	@echo "  zip     - Create plugin zip file"
	@echo "  install - Install plugin to Calibre"
	@echo "  test    - Install and test the plugin"
	@echo "  clean   - Remove built files"
	@echo "  help    - Show this help message"