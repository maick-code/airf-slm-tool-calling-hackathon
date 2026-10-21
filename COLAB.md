# Entraînement Colab — Gemma 3 270M (T4)

## 403 GatedRepoError = licence, pas un bug de code

Hugging Face refuse le téléchargement tant que **le compte du token** n’a pas cliqué Agree.

1. Va sur https://huggingface.co/settings/tokens et note **quel compte** a créé `HF_TOKEN`.
2. **Déconnecte / reconnecte** Hugging Face avec **ce** compte.
3. Ouvre https://huggingface.co/google/gemma-3-270m-it  
   Tu dois voir **Agree and access repository** (pas seulement une page 404). Clique **Agree**.
4. Token : type **Read** (ou fine-grained avec *Read access to contents of all public gated repos you can access*).
5. Colab → 🔑 Secrets → nom exact `HF_TOKEN`, **Notebook access ON**.
6. **Runtime → Restart session** puis Run all.

Le notebook affiche `HF account: <nom>`. C’est **ce** nom qui doit avoir accepté Gemma.

Mettre le token dans les secrets **sans** Agree sur la page du modèle → 403 à chaque fois.

## T4

Après un OOM : **Disconnect and delete runtime**. Uniquement `google/gemma-3-270m-it` sur T4.
