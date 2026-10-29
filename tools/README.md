# Update the visual résumé

Edit `resume.json`, then run:

```sh
python -m pip install -r tools/requirements.txt
python tools/build_resume.py
python tools/build_resume.py --check
```

The builder creates desktop and mobile artwork in both light and dark themes. It checks text bounds, XML, and generated-file consistency. A content-derived image version prevents GitHub from displaying an older cached résumé.

The SVGs contain outlined Space Grotesk and Manrope typography, so GitHub needs no external font service. Fonts are distributed under the bundled SIL Open Font License files. Motion uses SVG-contained CSS and respects reduced-motion preferences. Repository and contact links live in the README, outside images.

Commit `resume.json`, generated assets, and `README.md` together. The source CV and local previews stay private.
