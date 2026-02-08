#!/bin/bash

# Configuration
FOLDER_NAME="pyban_private_mac"
BACKUP_DIR="/mnt/moo/backupsi/$(hostname)"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_NAME="${FOLDER_NAME}_${DATE}.tar.gz"

# Créer le répertoire de backup si nécessaire
mkdir -p "$BACKUP_DIR"

# Créer l'archive (exclure les fichiers .log)
tar -czvf "$BACKUP_DIR/$ARCHIVE_NAME" -C "$(dirname "$SOURCE_DIR")" --exclude="*.log" "$FOLDER_NAME"

echo "Backup créé: $BACKUP_DIR/$ARCHIVE_NAME"
