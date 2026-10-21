# Entraînement Colab (objectif ≥ 93 % dev)

L’entraînement **ne tourne pas dans ce sandbox** (pas de GPU). Il se fait sur **Google Colab T4**.

## 1. Secrets Colab

- `HF_TOKEN` — token Hugging Face (read)
- `GH_TOKEN` (optionnel) — PAT GitHub pour pousser `submission.zip`

**Si tu as `403 GatedRepoError` sur FunctionGemma :** tu n’as pas accepté la licence, ou le secret `HF_TOKEN` n’est pas branché.

1. Connecte-toi sur Hugging Face
2. Ouvre https://huggingface.co/google/functiongemma-270m-it **et** https://huggingface.co/google/gemma-3-270m-it
3. Clique **Agree and access repository**
4. Colab → 🔑 Secrets → `HF_TOKEN` = ton token (`hf_...`), notebook **autorisé** à y accéder
5. Relance **Runtime → Restart and run all**

Sans licence, le notebook bascule tout seul sur **`Qwen/Qwen2.5-1.5B-Instruct`** (ouvert, ≤ 4B).

## 2. Lancer

Ouvre `train_colab.ipynb` dans Colab (GPU T4).

Le notebook :

1. Télécharge train/dev
2. Fine-tune FunctionGemma / Gemma / Qwen, LoRA r=32, **2 epochs**, **tous les exemples** (sauf 300 val)
3. Score sur 300 val — stop si < 90 %
4. Écrit `submission.json` + `submission.zip`
5. Pousse sur GitHub si `GH_TOKEN` est défini

Pour viser plus haut (après avoir accepté Gemma) :

```python
os.environ["MODEL_NAME"] = "google/gemma-3-1b-it"  # ou gemma-3-4b-it
EPOCHS = 2
```

Baseline officiel : Gemma 3 270M × 15k × 1 epoch = **88.35 %**. FunctionGemma est déjà à **77 %** avec seulement 3k.

## 3. Soumission locale / GitHub

```bash
python generate_submission.py --rules-only --push
python generate_submission.py --adapter ./adapter --model Qwen/Qwen2.5-1.5B-Instruct --push
```

Upload **`submission.zip`** sur [Codabench Participate](https://www.codabench.org/competitions/18354/#/participate-tab).
