# Entraînement Colab (objectif ≥ 93 % dev)

L’entraînement **ne tourne pas dans ce sandbox** (pas de GPU). Il se fait sur **Google Colab T4**.

## 1. Secrets Colab

- `HF_TOKEN` — compte Hugging Face ayant accepté la licence [FunctionGemma](https://huggingface.co/google/functiongemma-270m-it) (et Gemma si tu changes de modèle)
- `GH_TOKEN` (optionnel) — PAT GitHub pour pousser `submission.zip`

## 2. Lancer

Ouvre `train_colab.ipynb` dans Colab (GPU T4).

Le notebook :

1. Télécharge train/dev
2. Fine-tune **FunctionGemma 270M** LoRA r=32, **2 epochs**, **tous les exemples** (sauf 300 val)
3. Score sur 300 val — stop si &lt; 90 %
4. Écrit `submission.json` + `submission.zip`
5. Pousse sur GitHub si `GH_TOKEN` est défini

Pour viser plus haut : dans la cellule modèle,

```python
MODEL_NAME = "google/gemma-3-1b-it"  # ou gemma-3-4b-it
EPOCHS = 2
```

Baseline officiel : Gemma 3 270M × 15k × 1 epoch = **88.35 %**. FunctionGemma est déjà à **77 %** avec seulement 3k.

## 3. Soumission locale / GitHub

```bash
# fallback règles (sans GPU)
python generate_submission.py --rules-only --push

# après avoir téléchargé adapter/ depuis Colab
python generate_submission.py --adapter ./adapter --model google/functiongemma-270m-it --push
```

Upload **`submission.zip`** sur [Codabench Participate](https://www.codabench.org/competitions/18354/#/participate-tab).
