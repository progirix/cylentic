# Connecter un MCP humaniseur à Cursor

## Ce qui a déjà été fait côté agent
- Installation locale de **humanize-mcp** (gratuit) sur la VM cloud.
- Fichier projet `.cursor/mcp.json` préparé pour **humantext** (portable sur ton PC).

## Ce que tu dois faire (2 minutes) — obligatoire

Je ne peux pas activer un MCP dans **ton** Cursor Desktop à ta place. Sans cette étape, l’agent cloud ne verra pas l’outil.

### Option recommandée : humantext (500 mots gratuits)

1. Va sur https://humantext.pro et crée un compte.
2. Génère une **API key**.
3. Ouvre le fichier du projet : `.cursor/mcp.json`
4. Remplace `REMPLACE_PAR_TA_CLE_HUMANTEXT` par ta clé.
5. Dans Cursor : **Settings → MCP** → refresh / restart.
6. Relance une conversation agent et dis : « utilise humantext pour humaniser ce paragraphe ».

Config attendue :

```json
{
  "mcpServers": {
    "humantext": {
      "command": "npx",
      "args": ["-y", "@humantext/mcp-server"],
      "env": {
        "HUMANTEXT_API_KEY": "ta_vraie_cle"
      }
    }
  }
}
```

### Option locale gratuite : humanize-mcp

Surtout utile en **anglais**. Sur du **français**, le test a montré des insertions anglaises (à éviter pour le rapport).

Si tu veux quand même l’installer sur ton PC :

```bash
git clone https://github.com/kitfoxs/humanize-mcp.git
cd humanize-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Puis dans `~/.cursor/mcp.json` pointe vers le `python` du venv et `server.py`.

## Après connexion

Dis-moi « MCP prêt » : on humanise le rapport, on garde annexes B et D, on retire A et C.
