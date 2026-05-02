# BD Creator — V1 Specification (Web App)

## 1. Objectif

Créer une application web permettant de composer des planches de bande dessinée simplement, à partir de :

* gabarits prédéfinis
* bibliothèque d’images
* textes libres dans les cases

L’outil est destiné à des utilisateurs non dessinateurs.

---

## 2. Architecture globale

### 2.1 Stack

```txt
Frontend : React (ou équivalent)
Backend : FastAPI (Python)
Base de données : PostgreSQL
Stockage fichiers : filesystem ou S3-compatible
Authentification : Keycloak (SSO)
```

---

### 2.2 Contraintes

* application web uniquement (pas de PWA en V1)
* utilisateur **obligatoirement authentifié**
* aucune fonctionnalité offline

---

## 3. Authentification

### 3.1 Principe

* authentification via Keycloak
* utilisation d’un token (JWT ou équivalent)
* chaque requête backend doit être authentifiée

---

### 3.2 Règles

* aucun accès anonyme
* toutes les BD sont liées à un utilisateur
* isolation stricte des données

```txt
Comic.user_id obligatoire
```

---

## 4. Modèle de données

### 4.1 Comic (BD)

```txt
Comic
- id
- user_id
- name
- created_at
```

---

### 4.2 Page (Planche)

```txt
Page
- id
- comic_id
- template_id
- page_number
- status: "draft" | "validated"
- rendered_image_url
- artifact_generated_at
```

---

### 4.3 Template (Gabarit)

```txt
Template
- id
- name
- columns
- rows
```

---

### 4.4 Slot

```txt
Slot
- id
- template_id
- col_start
- row_start
- col_span
- row_span
- geometry_type: "rectangle"
```

---

### 4.5 Panel (Case)

```txt
Panel
- id
- page_id
- slot_id
- reading_order
- image_asset_id
- crop_zoom
- crop_offset_x
- crop_offset_y
```

---

### 4.6 TextBlock

```txt
TextBlock
- id
- panel_id
- content
- x
- y
- width
- height
- font_size
- bubble_style
```

Contraintes :

* coordonnées relatives à la case
* ne peut pas sortir de la case

---

### 4.7 Asset (Image)

```txt
Asset
- id
- user_id
- name
- file_path
- created_at
```

---

## 5. Base de données

### 5.1 Obligatoire

* PostgreSQL utilisé
* migrations SQL requises

---

### 5.2 Contraintes

* FK strictes
* index sur :

  * comic_id
  * page_id
  * panel_id
  * user_id

---

### 5.3 Migrations

* système de migration obligatoire (Alembic recommandé)
* aucune création manuelle en base

---

## 6. Gestion des images

### 6.1 Import

Nom généré automatiquement :

```txt
{comic_name}_planche-{page_number}_img-{increment}
```

Nom modifiable ensuite.

---

### 6.2 Règles

* bibliothèque globale par utilisateur
* tri alphabétique
* recherche texte
* réutilisation possible dans plusieurs cases

---

## 7. UX

### 7.1 Navigation

* liste des BD
* liste des planches
* vue planche

---

### 7.2 Création planche

* sélection d’un gabarit
* gabarit non modifiable ensuite

---

### 7.3 Édition case

* clic → ouverture modal

Contenu :

#### Image

* sélection dans bibliothèque
* zoom
* déplacement

#### Texte

* ajout
* déplacement
* redimensionnement

---

### 7.4 Contraintes

* pas d’édition directe sur la planche
* pas de drag & drop global

---

## 8. Gabarits

* codés en dur en V1
* non éditables

Exemples :

* 1 case
* 2 vertical
* 2 horizontal
* 3 cases
* 4 cases

---

## 9. Validation des planches

### 9.1 États

```txt
draft → modifiable
validated → non modifiable
```

---

### 9.2 Modification

Modifier une planche validée :

* repasse en draft
* supprime l’artefact JPEG
* reset des champs artefact

---

## 10. Génération des artefacts

### 10.1 Principe

* déclenché au niveau de la BD
* pas automatique

---

### 10.2 Action utilisateur

```txt
Générer les artefacts manquants
```

---

### 10.3 Comportement

Pour chaque planche :

* si pas d’image → générer
* sinon → ignorer

---

### 10.4 Génération

* rendu fidèle au DOM
* export JPEG
* stockage
* mise à jour :

```txt
rendered_image_url
artifact_generated_at
```

---

### 10.5 Invalidation

Si modification :

* suppression JPEG
* reset champs

---

## 11. Backend (FastAPI)

### 11.1 Responsabilités

* CRUD complet
* gestion auth Keycloak
* upload images
* génération artefacts
* suppression artefacts

---

### 11.2 Structure attendue

```txt
/api/comics
/api/pages
/api/panels
/api/assets
/api/templates
/api/render
```

---

## 12. Points critiques

### 12.1 Cadrage image

* fluide
* sans déformation

### 12.2 Texte

* lisible
* contenu maîtrisé

### 12.3 Simplicité

```txt
Si ça ressemble à Canva → refuser
```

---

## 13. Philosophie

Ce produit est :

* un outil de composition
* basé sur des gabarits
* simple
* rapide

Ce n’est pas :

* un outil de dessin
* un éditeur graphique avancé

---

## 14. Évolutions futures (non V1)

* formes complexes (SVG)
* chevauchement
* bulles avancées
* éditeur de gabarits
* drag & drop

---

## 15. Règle d’or

> Une case est une unité narrative indépendante.
> Sa position et sa forme sont définies uniquement par le gabarit.

---
