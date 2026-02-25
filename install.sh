#!/bin/bash
# DRAGO Model Runner - Installation Script
# =========================================

set -e

echo "🐉 DRAGO Model Runner - Instalacion"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
echo -n "Verificando Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}OK${NC} (Python $PYTHON_VERSION)"
else
    echo -e "${RED}ERROR${NC}"
    echo "Python 3 no encontrado. Instala Python 3.10+ primero."
    exit 1
fi

# Check tkinter
echo -n "Verificando tkinter... "
if python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}No encontrado${NC}"
    echo "Instalando python3-tk..."
    sudo apt install python3-tk -y
    echo -e "${GREEN}tkinter instalado${NC}"
fi

# Check pip
echo -n "Verificando pip... "
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}Instalando pip...${NC}"
    sudo apt install python3-pip -y
fi

# Check Ollama
echo -n "Verificando Ollama... "
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -1)
    echo -e "${GREEN}OK${NC} ($OLLAMA_VERSION)"
else
    echo -e "${YELLOW}No encontrado${NC}"
    echo ""
    read -p "Deseas instalar Ollama ahora? (s/n): " install_ollama
    if [[ $install_ollama == "s" || $install_ollama == "S" ]]; then
        echo "Instalando Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        echo -e "${GREEN}Ollama instalado${NC}"
    else
        echo -e "${YELLOW}AVISO: Necesitaras Ollama para usar la aplicacion${NC}"
    fi
fi

# Create virtual environment
echo ""
echo "Creando entorno virtual..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}Entorno virtual creado${NC}"
else
    echo "Entorno virtual ya existe"
fi

# Remove old venv if exists
if [ -d "venv" ] && [ -d ".venv" ]; then
    rm -rf venv
    echo "Eliminado entorno virtual antiguo (venv/)"
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo ""
echo "Instalando dependencias..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}Dependencias instaladas${NC}"

# Create models directory
MODELS_DIR="$HOME/ai-models"
if [ ! -d "$MODELS_DIR" ]; then
    mkdir -p "$MODELS_DIR"
    echo "Directorio de modelos creado: $MODELS_DIR"
fi

# Create launch script
echo ""
echo "Creando script de lanzamiento..."
cat > run.sh << 'RUNEOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source .venv/bin/activate
python main.py "$@"
RUNEOF
chmod +x run.sh
echo -e "${GREEN}Script creado: run.sh${NC}"

# Create desktop entry (optional)
echo ""
read -p "Crear acceso directo en el escritorio? (s/n): " create_desktop
if [[ $create_desktop == "s" || $create_desktop == "S" ]]; then
    DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
    DESKTOP_FILE="$DESKTOP_DIR/drago-model-runner.desktop"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DRAGO Model Runner
Comment=Gestion de modelos LLM locales
Exec=bash -c 'cd "$SCRIPT_DIR" && source .venv/bin/activate && python main.py'
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Development;
StartupWMClass=drago-model-runner
EOF
    chmod +x "$DESKTOP_FILE"
    # Trust the desktop file on GNOME
    gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
    echo -e "${GREEN}Acceso directo creado${NC}"
fi

echo ""
echo "===================================="
echo -e "${GREEN}Instalacion completada${NC}"
echo ""
echo "Para ejecutar la aplicacion:"
echo "  ./run.sh"
echo ""
echo "O directamente:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""

# Offer to start now
read -p "Ejecutar DRAGO Model Runner ahora? (s/n): " run_now
if [[ $run_now == "s" || $run_now == "S" ]]; then
    echo "Iniciando..."
    python main.py
fi
