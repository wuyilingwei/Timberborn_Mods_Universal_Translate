#!/bin/bash
set -eu

echo "----------------------------------------"

# REMINDER: Before running this script, ensure that:
# 1. SteamCMD is installed and configured correctly.
# 2. You are logged into SteamCMD with the appropriate account.
# 3. The 'gh' CLI tool is installed and authenticated with GitHub.
# 4. Python and required packages are installed.
# 5. The 'zip' utility is installed.
# =========== Path Config ===========
BASE_DIR="/home/Timberborn"
GIT_DIR="$BASE_DIR/git"
STEAMCMDDIR="$BASE_DIR/steam"
MOD_INFO_DIR="$BASE_DIR/mod_info"
RELEASE_DIR="$BASE_DIR/release"
CONTEXT_DIR="$GIT_DIR/mod"
MANIFEST_FILE="$MOD_INFO_DIR/manifest.json"
VENV_DIR="$BASE_DIR/venv"

# =========== Mod Config ===========
APPID="1062090"
PUBLISHEDFILEID="3346918947"

# =========== GitHub Config ===========
REPO_OWNER="wuyilingwei"
REPO_NAME="Timberborn_Mods_Universal_Translate"

# =========== Command Config ===========
GETUPDATE=true
FORCE_UPDATE=false
OVERWRITE=false
PUSH_STEAM=true
PUSH_GITHUB=true

# =========== Command Line Args ===========
for arg in "$@"; do
    case "$arg" in
        -force)
            FORCE_UPDATE=true
            ;;
        -overwrite)
            OVERWRITE=true
            ;;
        -skip_update)
            GETUPDATE=false
            ;;
        -no_steam)
            PUSH_STEAM=false
            ;;
        -no_github)
            PUSH_GITHUB=false
            ;;
    esac
done

# =========== Ensure Virtual Environment ===========
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Virtual environment not found. Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$BASE_DIR/requirments.txt"
else
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
fi

# =========== Main ===========
echo "Run time:$(date)"

# =========== Fetch Updates ===========
cd "$GIT_DIR"

echo "Fetching origin updates..."
git fetch origin main

LOCAL=$(git rev-parse main)
REMOTE=$(git rev-parse origin/main)

echo "Local commit: $LOCAL"
echo "Remote commit: $REMOTE"

# =========== Check Updates ===========
if [ "$LOCAL" != "$REMOTE" ] || [ "$FORCE_UPDATE" = true ]; then
    if [ "$LOCAL" != "$REMOTE" ] && [ "$GETUPDATE" = true ]; then
        echo "Detected updates, pulling..."
    else
        echo "Forced update, pulling..."
    fi

    git pull origin main
    
    mkdir -p "$MOD_INFO_DIR"
    
    # =========== Update Version ===========
    if [ -f "$MANIFEST_FILE" ]; then
        if [ "$OVERWRITE" = true ]; then
            echo "enabled -overwrite, skip version update."
            new_version=$(grep -oP '"Version":\s*"\K2\.1\.\d+' "$MANIFEST_FILE" || echo "")
        else
            current_version=$(grep -oP '"Version":\s*"\K2\.1\.\d+' "$MANIFEST_FILE" || echo "")
            if [ -z "$current_version" ]; then
                echo "Error: Can't find version in manifest.json!"
            else
                echo "Now version: $current_version"
                last_digit=$(echo "$current_version" | awk -F'.' '{print $3}')
                version_head=$(echo "$current_version" | awk -F'.' '{print $1"."$2}')
                new_last_digit=$((last_digit + 1))
                new_version="${version_head}.${new_last_digit}"
                echo "Version updated to: $new_version"
                sed -i "0,/${current_version}/s/${current_version}/${new_version}/" "$MANIFEST_FILE"
            fi
        fi
    else
        echo "No manifest.json found, skip version update."
    fi

    # =========== Create Release ===========
    rm -rf "$RELEASE_DIR"
    mkdir -p "$RELEASE_DIR"

    # 检查 CONTEXT_DIR 是否存在且非空
    if [ -d "$CONTEXT_DIR" ] && [ "$(ls -A "$CONTEXT_DIR")" ]; then
        cp -r "$CONTEXT_DIR"/* "$RELEASE_DIR"/
    else
        echo "Warning: $CONTEXT_DIR is empty or does not exist. Skipping copy."
    fi

    cp -r "$MOD_INFO_DIR"/thumbnail.png "$RELEASE_DIR"/
    cp -r "$MOD_INFO_DIR"/workshop_data.json "$RELEASE_DIR"/
    cp -r "$MOD_INFO_DIR"/License.txt "$RELEASE_DIR"/

    # 清理目录
    DATA_DIR="$GIT_DIR/data"
    MOD_DIR="$GIT_DIR/mod"
    echo "Cleaning up old localization directories..."
    find "$MOD_DIR" -type d -name "version-*" -exec rm -rf {} +

    # =========== Convert TOML to CSV ===========
    echo "Converting TOML files to CSV..."
    PYTHON_LOG_FILE="$BASE_DIR/python_conversion.log"
    PYTHON_SCRIPT="$BASE_DIR/convert_toml_to_csv.py"
    
    # 清空日志文件
    > "$PYTHON_LOG_FILE"
    
    # 检查Python脚本文件是否存在
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        echo "Error: Python script $PYTHON_SCRIPT not found!"
        exit 1
    fi
    
    # 调用独立的Python脚本并重定向输出
    python3 "$PYTHON_SCRIPT" "$DATA_DIR" "$MOD_DIR" 2>&1 | tee "$PYTHON_LOG_FILE"

    echo "TOML to CSV conversion completed."

    # =========== 创建manifest.json到release目录 ===========
    echo "Creating manifest.json in release directory..."
    mkdir -p "$RELEASE_DIR"
    cp "$MOD_INFO_DIR/manifest.json" "$RELEASE_DIR/"

    # =========== Push to Steam Workshop ===========
    if [ "$PUSH_STEAM" = true ]; then
        cd "$STEAMCMDDIR"
        changenote="Automated Updates ${new_version:-unknown}"

        cat <<EOF > workshop.vdf
"workshopitem"
{
    "appid"            "$APPID"
    "publishedfileid"  "$PUBLISHEDFILEID"
    "contentfolder"    "$RELEASE_DIR"
    "changenote"       "$changenote"
}
EOF

        echo "Content of workshop.vdf:"
        cat workshop.vdf

        echo "Uploading to Steam Workshop..."
        "$STEAMCMDDIR/steamcmd.sh" \
            +login wuyilingwei \
            +workshop_build_item "$(pwd)/workshop.vdf" \
            +quit || {
                echo "Error: SteamCMD Upload Failed!"
            }
    else
        echo "Info: -push_steam is disabled by user; skipping Steam Workshop upload."
    fi

    # =========== Push to GitHub ===========
    if [ "$PUSH_GITHUB" = true ]; then
        cd "$GIT_DIR"
        GIT_TAG="v${new_version}"
        echo "Checking or creating Git tag: $GIT_TAG"

        if ! git rev-parse "$GIT_TAG" >/dev/null 2>&1; then
            git tag "$GIT_TAG" || {
                echo "Error: Failed to create tag $GIT_TAG!"
            }
            git push origin "$GIT_TAG"
        else
            echo "Tag $GIT_TAG already exists. Skip creating tag."
        fi

        cd "$BASE_DIR"
        TMP_FOLDER="Timberborn_Mods_Universal_Translate_Github"
        rm -rf "$TMP_FOLDER"
        cp -r release "$TMP_FOLDER"

        RELEASE_ZIP="${new_version}.zip"
        echo "Creating release archive: $RELEASE_ZIP"
        zip -r "$RELEASE_ZIP" "$TMP_FOLDER"

        rm -rf "$TMP_FOLDER"

        RELEASE_NOTES="Automated Update to $new_version"
        
        # 检查Python日志文件是否有内容
        if [ -f "$PYTHON_LOG_FILE" ] && [ -s "$PYTHON_LOG_FILE" ]; then
            echo "Python conversion log found, adding to release notes..."
            PYTHON_LOG_CONTENT=$(cat "$PYTHON_LOG_FILE")
            
            # 提取错误信息（以[ERROR]开头的行）
            ERROR_LINES=$(echo "$PYTHON_LOG_CONTENT" | grep "^\[ERROR\]" || true)
            
            if [ -n "$ERROR_LINES" ]; then
                RELEASE_NOTES="$RELEASE_NOTES

<details>
<summary>Building Log (Occur Error)</summary>

**Error Messages:**
\`\`\`
$ERROR_LINES
\`\`\`

<details>
<summary>Full Log</summary>

\`\`\`
$PYTHON_LOG_CONTENT
\`\`\`
</details>

</details>"
            else
                RELEASE_NOTES="$RELEASE_NOTES

<details>
<summary>Building Log</summary>

No errors found during conversion.

<details>
<summary>Full Log</summary>

\`\`\`
$PYTHON_LOG_CONTENT
\`\`\`
</details>

</details>"
            fi
        fi

        echo "Creating GitHub Release $GIT_TAG in $REPO_OWNER/$REPO_NAME..."
        gh release create "$GIT_TAG" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --title "$GIT_TAG" \
            --notes "$RELEASE_NOTES" \
            "$RELEASE_ZIP" || {
                echo "Error: GitHub Release creation failed!"
            }

        if [ -f "$RELEASE_ZIP" ]; then
            echo "Cleaning up $RELEASE_ZIP..."
            rm -f "$RELEASE_ZIP"
        fi
        
        # 清理日志文件
        if [ -f "$PYTHON_LOG_FILE" ]; then
            echo "Cleaning up Python log file..."
            rm -f "$PYTHON_LOG_FILE"
        fi

        echo "GitHub Release $GIT_TAG created and $RELEASE_ZIP uploaded."
    else
        echo "Info: -push_github is disabled by user; skipping GitHub release."
    fi

else
    echo "No updates detected, skip."
fi

exit 0
