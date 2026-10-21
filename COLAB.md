# Entraînement Colab — Gemma 3 270M (T4)

## 403 GatedRepoError = licence, pas un bug de code

Hugging Face refuse le téléchargement tant que **le compte du token** n’a pas cliqué Agree.

1. Va sur https://huggingface.co/settings/tokens et note **quel compte** a créé `HF_TOKEN`.
2. **Déconnecte / reconnecte** Hugging Face avec **ce** compte.
3. Ouvre https://huggingface.co/google/gemma-3-270m-it  
   Tu dois voir **Agree and access repository**. Clique **Agree**.
4. Token : type **Read** (ou fine-grained avec accès aux repos gated).
5. Colab → 🔑 Secrets → nom exact `HF_TOKEN`, **Notebook access ON**.
6. Pour GitHub : secret **`GH_TOKEN`** ou **`GITHUB_TOKEN`** (PAT avec droit `repo`), **Notebook access ON** aussi. Sinon le notebook affiche `No GH_TOKEN` même si le secret existe.
7. **Runtime → Restart session** puis Run all.

Le notebook affiche `HF account: <nom>`. C’est **ce** nom qui doit avoir accepté Gemma.

## 2e run (leaderboard 88.9 % → viser 92 %+)

`train_colab.ipynb` : **FunctionGemma 270M**, **1 epoch**, T4.

Accepte aussi https://huggingface.co/google/functiongemma-270m-it puis Runtime → Restart → Run all.

Ne pas réentraîner 2 epochs Gemma 270M (overfit).
