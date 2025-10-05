#!/bin/bash

# 🚀 Amazing Interactive File Opener for VS Code Workspace
# Opens program files one by one with beautiful terminal UI

# Colors and styling
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Emojis for file types
declare -A FILE_EMOJIS=(
    [".py"]="🐍"
    [".js"]="📜"
    [".ts"]="💙"
    [".tsx"]="⚛️"
    [".html"]="🌐"
    [".css"]="🎨"
    [".json"]="📋"
    [".md"]="📝"
    [".yaml"]="⚙️"
    [".yml"]="⚙️"
    [".sh"]="💻"
    [".lock"]="🔒"
)

# Function to get file emoji
get_file_emoji() {
    local file="$1"
    local extension="${file##*.}"
    echo "${FILE_EMOJIS[.${extension}]:-📄}"
}

# Function to get file type color
get_file_color() {
    local file="$1"
    local extension="${file##*.}"
    case "$extension" in
        py) echo "$GREEN" ;;
        js|ts|tsx) echo "$YELLOW" ;;
        html) echo "$BLUE" ;;
        css) echo "$CYAN" ;;
        json|yaml|yml) echo "$PURPLE" ;;
        md) echo "$WHITE" ;;
        *) echo "$NC" ;;
    esac
}

# Function to print fancy header
print_header() {
    clear
    echo -e "${BOLD}${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                    🚀 AMAZING FILE OPENER 🚀                     ║"
    echo "║                   Interactive VS Code Launcher                    ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Function to print progress bar
print_progress() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf "${CYAN}Progress: [${GREEN}"
    printf "%*s" $filled | tr ' ' '█'
    printf "${WHITE}"
    printf "%*s" $empty | tr ' ' '░'
    printf "${CYAN}] ${YELLOW}%d%%${NC} (${current}/${total})\n" $percentage
}

# Function to show fast loading (no animation delays)
show_opening() {
    local message="$1"
    echo -e "${BLUE}${message}...${NC}"
}

# Function to print compact file info
print_file_info() {
    local current=$1
    local total=$2
    local file="$3"
    local relative_path=${file#/home/pranay/Music/niraj/}
    local emoji=$(get_file_emoji "$file")
    local color=$(get_file_color "$file")

    # Clear the line and print progress + file info on same line
    printf "\r${CYAN}[%d/%d]${NC} ${color}${emoji} ${relative_path}${NC} ${GREEN}✅${NC}" "$current" "$total"
}

# Main function
main() {
    print_header

    echo -e "${YELLOW}🔍 Scanning workspace for program files...${NC}"
    echo ""

    # Find all program files
    mapfile -t files < <(find /home/pranay/Music/niraj -type f \( \
        -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" \
        -o -name "*.html" -o -name "*.css" -o -name "*.json" \
        -o -name "*.md" -o -name "*.yaml" -o -name "*.yml" \
        -o -name "*.sh" \) \
        -not -path "*/logs/*" \
        -not -path "*/__pycache__/*" \
        -not -path "*/__pycache__/*" \
        -not -path "*/backend/tests/*" \
        -not -path "*/node_modules/*" \
        -not -path "*/.pytest_cache/*" \
        -not -path "*/.mypy_cache/*" \
        -not -path "*/.git/*" \
        -not -path "*/migrations/*" \
        -not -name "*.lock" \
        | sort)

    total_files=${#files[@]}

    if [ $total_files -eq 0 ]; then
        echo -e "${RED}❌ No program files found!${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Found ${BOLD}${total_files}${NC}${GREEN} program files!${NC}"
    echo ""

    # Ask user for confirmation
    echo -e "${CYAN}🤔 Choose opening mode:${NC}"
    echo -e "${GREEN}  y) ${WHITE}Fast mode - Open files quickly (0.05s delay)${NC}"
    echo -e "${PURPLE}  t) ${WHITE}Turbo mode - Open all files instantly${NC}"
    echo -e "${YELLOW}  s) ${WHITE}Selective mode - Choose which files to open${NC}"
    echo -e "${RED}  n) ${WHITE}Cancel${NC}"
    echo ""
    echo -e "${CYAN}Your choice: ${NC}"
    read -r choice

    case $choice in
        [Yy]*)
            echo ""
            echo -e "${GREEN}🚀 Starting fast file opening...${NC}"
            echo -e "${YELLOW}💡 Files will open rapidly - watch the progress!${NC}"
            echo ""

            # Show overall progress bar
            print_progress 0 $total_files
            echo ""

            for i in "${!files[@]}"; do
                file="${files[$i]}"

                # Open file in background for speed
                code "$file" &

                # Show file being opened (very fast display)
                print_file_info $((i + 1)) $total_files "$file"

                # Very short delay to see the file name (much faster than before)
                sleep 0.1
            done

            echo ""
            echo ""
            print_progress $total_files $total_files
            echo ""
            echo -e "${BOLD}${GREEN}🎉 All ${total_files} files opened successfully! 🎉${NC}"
            echo -e "${CYAN}💫 Opening completed in super-fast mode!${NC}"
            ;;

        [Tt]*)
            echo ""
            echo -e "${PURPLE}🚀 TURBO MODE ACTIVATED! 🚀${NC}"
            echo -e "${YELLOW}⚡ Opening ALL files instantly...${NC}"
            echo ""

            # Open all files at once in background
            for file in "${files[@]}"; do
                code "$file" &
            done

            # Show rapid file listing
            echo -e "${CYAN}Files being opened:${NC}"
            for i in "${!files[@]}"; do
                file="${files[$i]}"
                relative_path=${file#/home/pranay/Music/niraj/}
                emoji=$(get_file_emoji "$file")
                color=$(get_file_color "$file")
                printf "${color}${emoji} ${relative_path}${NC} "

                # Print 3 files per line for better readability
                if (( (i + 1) % 3 == 0 )); then
                    echo ""
                fi
                sleep 0.07
            done
            echo ""
            echo ""
            echo -e "${BOLD}${PURPLE}⚡ TURBO COMPLETE! ${total_files} files opened instantly! ⚡${NC}"
            ;;

        [Ss]*)
            echo ""
            echo -e "${YELLOW}🎯 Selective mode - Choose files to open:${NC}"
            echo ""

            for i in "${!files[@]}"; do
                file="${files[$i]}"
                relative_path=${file#/home/pranay/Music/niraj/}
                emoji=$(get_file_emoji "$file")
                color=$(get_file_color "$file")

                echo -e "${BOLD}$((i + 1)).${NC} ${color}${emoji} ${relative_path}${NC}"
                echo -e "${CYAN}   Open this file? ${YELLOW}(y/n/q to quit)${NC}: "
                read -r file_choice

                case $file_choice in
                    [Yy]*)
                        show_opening "Opening in VS Code"
                        code "$file" &
                        echo -e "${GREEN}✅ Opened!${NC}"
                        ;;
                    [Qq]*)
                        echo -e "${YELLOW}👋 Exiting selective mode...${NC}"
                        break
                        ;;
                    *)
                        echo -e "${BLUE}⏭️  Skipped${NC}"
                        ;;
                esac
                echo ""
            done
            ;;

        *)
            echo -e "${YELLOW}👋 Operation cancelled. Have a great day!${NC}"
            exit 0
            ;;
    esac
}

# Show fancy goodbye message
show_goodbye() {
    echo ""
    echo -e "${BOLD}${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                     🎉 Mission Accomplished! 🎉                  ║"
    echo "║                 Happy coding with VS Code! 💻✨                  ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Run the main function
main
show_goodbye
