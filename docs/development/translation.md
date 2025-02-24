# Manage translations

## Requirements

Qt Linguist tools are used to manage translations. Typically on Ubuntu:

```bash
sudo apt install qttools5-dev-tools
```

## Workflow

1. Complete `plugin_translation.pro` in `i18n` folder with what you wish to translate (`.ui` or `.py` file) or run the script:

    ```sh
    python scripts/generate_translation_profile.py
    ```

2. Update `.ts` files:

    ```bash
    pylupdate5 -noobsolete -verbose qduckdb/resources/i18n/plugin_translation.pro
    ```

3. Translate your text using QLinguist or directly into `.ts` files (with QtLinguist):

    Shortcut: CTRL + Enter to validate and move on to the next translation.

4. Compile it:

    It's only necessary for local development since CI build and ship it.

    ```bash
    lrelease qduckdb/resources/i18n/*.ts
    ```
