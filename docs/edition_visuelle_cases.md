# Modification — Édition visuelle des cases

## Objectif

Améliorer l’éditeur de planche pour permettre un rendu visuel fidèle pendant l’édition.

L’utilisateur doit pouvoir :

- voir la planche complète ;
- cliquer sur une case ;
- éditer cette case dans un panneau latéral ;
- choisir une image ;
- cadrer l’image (zoom + déplacement) ;
- ajouter des textes ;
- déplacer les textes à la souris ;
- configurer couleurs et transparence.

---

## Choix UX

Utiliser un panneau latéral d’édition.

- La planche reste visible à gauche ;
- Le panneau latéral est toujours visible en mode brouillon ;
- Il est masqué si la planche est validée.

Si aucune case n’est sélectionnée, afficher :

```txt
Sélectionne une case pour l’éditer.
```

Ne pas éditer directement dans la planche en V1.

---

## Composants frontend

Créer un composant central :

### PanelCanvas

Utilisé pour :

* affichage dans la planche ;
* affichage dans le panneau latéral.

Props :

* `panel`
* `slot`
* `asset`
* `textBlocks`
* `mode: "preview" | "edit"`
* callbacks optionnels

Objectif : un seul moteur de rendu.

---

## Affichage de la planche

Dans `PageEditorPage.tsx` :

Remplacer l’affichage actuel des cases (ordre uniquement).

Chaque case doit afficher :

* image (si présente) ;
* textes ;
* contour ;
* état actif.

Utiliser le template existant pour la grille.

---

## Chargement des textes

Actuellement :

* les textes sont chargés uniquement pour la case active.

Modification :

* charger les textes pour toutes les cases.

Option simple :

* appeler `/api/panels/{id}/text-blocks` pour chaque panel ;
* construire `textBlocksByPanelId`.

---

## Image dans la case

Fonctionnalités :

* sélection depuis assets ;
* affichage dans la case ;
* zoom ;
* déplacement X/Y ;
* reset.

Champs utilisés :

* `crop_zoom`
* `crop_offset_x`
* `crop_offset_y`

UI panneau latéral :

* zoom +
* zoom -
* gauche
* droite
* haut
* bas
* reset

Pas de drag image en V1.

---

## Textes

Chaque case contient plusieurs blocs texte.

### Champs UI

* textarea (contenu)
* text_color (hex)
* background_color (hex)
* background_opacity (slider 0 → 1)
* font_size
* width
* height
* bouton supprimer

---

## Rendu des textes

Positionnement basé sur ratios :

* `x`, `y`, `width`, `height` ∈ [0,1]

Conversion CSS :

* left: x * 100%
* top: y * 100%
* width: width * 100%
* height: height * 100%

Les textes sont affichés en overlay.

---

## Couleurs et transparence

### Nouveaux champs TextBlock

* `text_color`
* `background_color`
* `background_opacity`

### Valeurs par défaut

* text_color = "#000000"
* background_color = "#ffffff"
* background_opacity = 1

### Rendu CSS

Convertir en rgba :

```txt
#000000 + 0.5 → rgba(0,0,0,0.5)
```

Appliquer :

* color
* background
* padding léger
* border-radius simple

---

## Déplacement des textes

Interaction souris :

* clic maintenu sur le bloc texte ;
* déplacement libre ;
* relâchement → sauvegarde ;
* mise à jour de x/y ;

Contraintes :

* ratios 0 → 1 ;
* ne pas sortir complètement de la case ;
* pas de snap ;
* pas de resize souris en V1.

---

## Backend

Modifier :

* modèle SQLAlchemy `TextBlock`
* schémas Pydantic
* routes create/update
* types TypeScript

---

## Migration

Ajouter :

```txt
text_color varchar(16) not null default '#000000'
background_color varchar(16) not null default '#ffffff'
background_opacity float not null default 1
```

---

## Règles métier

* toute modification invalide l’artefact ;
* pas de génération automatique ;
* planche validée = non éditable ;
* panneau latéral masqué en mode validé.

---

## À ne pas faire

Ne pas implémenter :

* éditeur de gabarit ;
* drag image ;
* resize souris des textes ;
* bulles avancées ;
* calques ;
* auto-render.

---

## Résultat attendu

* rendu visuel réel dans la planche ;
* édition fluide via panneau latéral ;
* image cadrable ;
* textes visibles et déplaçables ;
* couleurs configurables ;
* cohérence rendu preview / édition.
