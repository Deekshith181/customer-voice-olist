"""Rule-based complaint themes for Portuguese review text (transparent, auditable, runs locally)."""
import re, unicodedata
import pandas as pd

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))

THEMES = {
    "Not received": [r"nao recebi", r"nao chegou", r"nao foi entregue", r"nao entreg", r"nunca chegou", r"ainda nao (chegou|recebi)",
                     r"nao (me )?(foi )?entreg", r"nada de (chegar|receber)", r"produto nao (chegou|veio)", r"ainda aguardo", r"continuo aguardando", r"nao (consegui )?receb"],
    "Late delivery": [r"atras", r"demor", r"fora do prazo", r"apos o prazo", r"depois do prazo", r"prazo (de entrega )?(estourou|vencido|nao)", r"entrega.{0,15}(lenta|tardia)", r"nao cumpr", r"prazo.{0,25}(prometido|combinado)", r"prometid", r"retirar nos correios|agencia dos correios"],
    "Damaged / defective": [r"quebrad", r"quebrou", r"danificad", r"defeit", r"avariad", r"amassad", r"rasgad", r"nao funciona", r"parou de funcionar", r"veio (com )?(riscado|trincado|rachado)"],
    "Wrong item": [r"produto errado", r"item errado", r"veio (outro|errado|diferente)", r"recebi (outro|errado|diferente)", r"trocado", r"cor diferente", r"tamanho (errado|diferente)", r"nao (era|foi) o (que|produto)", r"veio outr", r"enviaram (um|uma|o|a) .{0,25}(diferente|errad|feminin|masculin)", r"nao foi o (da|do) foto"],
    "Incomplete order": [r"faltando", r"faltou", r"incomplet", r"so (veio|chegou|recebi|entregaram|foi entregue)", r"apenas (um|uma|1|dois)", r"veio apenas", r"chegou apenas", r"so entreg", r"parte do pedido", r"(um|uma|1) dos (produtos|itens)", r"kit.{0,20}(incompleto|faltando)"],
    "Quality / not as described": [r"falsific", r"\bcopia\b", r"nao e original", r"nao (e|eh) (de )?(couro|original)", r"diferente (do|da|de) (anunci|descri|foto|propaganda|especific)", r"propaganda enganosa", r"anuncio enganador", r"enganos", r"\bfalso\b", r"picaretagem", r"sintetic", r"(pessima|ma|baixa|horrivel|fraca) qualidade", r"qualidade (pessima|ruim|horrivel|fraca|duvidosa|inferior)", r"nao (faz|fez) efeito", r"produto (ruim|fraco)"],
    "Seller service / refund": [r"vendedor", r"atendimento", r"sem resposta", r"nao (responde|respondeu|respond)", r"reembolso", r"estorno", r"devolu", r"dinheiro de volta", r"cancelaram|cancelou|cancelamento", r"nao (obtive|tive) (retorno|resposta)", r"loja (pessima|horrivel)", r"nao recomendo (a )?(loja|vendedor)"],
}
# Phrases that look like complaints but are praise; removed before matching
NEGATED = re.compile(r"(nao|sem|nunca) (teve |tive |houve )?(atras\w*|demor\w*|defeit\w*|problema\w*)|antes do prazo|dentro do prazo|nao (veio|chegou) (quebrad\w*|danificad\w*)|chegou (antes|rapido)")
PATTERNS = {k: re.compile("|".join(v)) for k, v in THEMES.items()}

def tag(df: pd.DataFrame, col: str = "comment") -> pd.DataFrame:
    txt = df[col].fillna("").map(lambda t: NEGATED.sub(" ", norm(t)))
    for k, p in PATTERNS.items():
        df[k] = txt.map(lambda t: bool(p.search(t)))
    df["any_theme"] = df[list(THEMES)].any(axis=1)
    return df
