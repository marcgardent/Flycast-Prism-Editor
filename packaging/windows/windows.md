# Guide : Packager un .exe Windows sous Linux avec Docker

Ce tutoriel explique comment créer un exécutable Windows (.exe) à partir d'un script Python en utilisant **Docker**, ce qui évite d'installer Wine ou Python Windows directement sur votre système Linux.

## 🚀 Pourquoi Docker ?
Packager pour Windows depuis Linux est complexe car PyInstaller ne fait pas de cross-compilation native. L'image Docker `cdrx/pyinstaller-windows` contient déjà :
- Un environnement **Wine** fonctionnel.
- **Python** (version Windows) installé.
- **PyInstaller** prêt à l'emploi.

---

## 1. Prérequis
- Avoir **Docker** installé et démarré.
- Un script Python (ex: `main.py`).
- Un fichier `requirements.txt` (si vous avez des dépendances).

## 2. Structure de votre projet
Organisez vos fichiers dans un dossier dédié :
```text
mon_projet/
├── src/
│   └── main.py
└── requirements.txt
```

## 3. La commande de compilation
Ouvrez votre terminal dans le dossier de votre projet et exécutez la commande suivante :

```bash
docker run --rm \
    -v "$(pwd):/src" \
    cdrx/pyinstaller-windows \
    "pip install -r requirements.txt; pyinstaller --onefile --windowed src/main.py"
```

### Explication des paramètres :
- `--rm` : Supprime le conteneur après le travail.
- `-v "$(pwd):/src"` : Monte votre dossier actuel dans le conteneur.
- `--onefile` : Compresse tout dans un seul fichier .exe.
- `--windowed` : Empêche l'ouverture d'une console (utile pour les apps GUI).

## 4. Récupérer le résultat
Une fois la commande terminée, un dossier **`dist/`** est créé dans votre projet.
Vous y trouverez votre fichier **`main.exe`** prêt à être envoyé sur Windows.

---

## 💡 Astuces avancées

### Ajouter une icône
Ajoutez l'argument `--icon=mon_icone.ico` dans la chaîne de commande PyInstaller.

### Gérer les erreurs Wine
Si le build échoue, essayez de supprimer les dossiers `build/` et `dist/` créés lors de tentatives précédentes avant de relancer Docker.

> **Note :** La première exécution peut être longue car Docker doit télécharger l'image (environ 1.5 Go). Les suivantes seront instantanées.
