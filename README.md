# Monitor de Preço — RTX 5060 8GB

Verifica o preço da RTX 5060 8GB em Mercado Livre, Kabum, Terabyte, Amazon e
Shopee, a cada 30 minutos, rodando 100% na nuvem (GitHub Actions, gratuito).
Te avisa no Telegram quando aparece um preço novo mais baixo do que qualquer
um já visto, ou abaixo do preço-alvo que você definir.

**Não precisa do seu PC ligado nem do navegador aberto** — roda direto nos
servidores do GitHub.

---

## Passo 1 — Criar o bot no Telegram (2 min)

1. No Telegram, procure por **@BotFather** e envie `/newbot`.
2. Escolha um nome e um usuário para o bot (precisa terminar em `bot`).
3. O BotFather vai te dar um **token** parecido com `123456789:AAExxxxxxx`.
   Guarde ele.
4. Envie qualquer mensagem para o seu bot recém-criado (ex: "oi").
5. No navegador, acesse (trocando `<TOKEN>` pelo seu token):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Procure por `"chat":{"id":` no JSON retornado — esse número é o seu
   **chat_id**. Guarde ele também.

## Passo 2 — Criar o repositório no GitHub

1. Crie uma conta no GitHub (se não tiver) e crie um **novo repositório**
   (pode ser público — assim os minutos do Actions são ilimitados e grátis).
2. Faça upload de todos os arquivos deste pacote mantendo a estrutura de
   pastas (o arquivo `.github/workflows/monitor.yml` precisa ficar
   exatamente nesse caminho).

## Passo 3 — Configurar os secrets

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

Adicione dois secrets:
- `TELEGRAM_BOT_TOKEN` → o token do Passo 1
- `TELEGRAM_CHAT_ID` → o chat_id do Passo 1

## Passo 4 — Ativar e testar

1. Vá na aba **Actions** do repositório e habilite os workflows se pedir.
2. Clique em **Monitor RTX 5060 8GB → Run workflow** para rodar manualmente
   e conferir se está tudo certo.
3. Veja o log da execução — ele mostra os preços encontrados em cada site.
4. A partir daí, ele roda sozinho a cada 30 minutos.

## Ajustando o preço-alvo

Edite o arquivo `config.json`:

```json
{
  "target_price": 1899.90,
  "sites_enabled": { ... }
}
```

Se `target_price` for `null`, você só é avisado quando aparece um preço mais
baixo do que qualquer um já registrado (`state.json`). Se definir um valor,
também é avisado sempre que o preço cair abaixo dele.

Para desativar um site específico (ex: se um scraper estiver instável),
mude `true` para `false` em `sites_enabled`.

---

## Sobre a confiabilidade de cada site

| Site | Método | Confiabilidade |
|---|---|---|
| Mercado Livre | API pública oficial | Alta — deve funcionar sempre |
| Kabum | Leitura da página de busca | Boa, mas pode quebrar se mudarem o layout |
| Terabyte | Leitura da página de busca | Boa, mas pode quebrar se mudarem o layout |
| Amazon | Leitura da página de busca | Instável — Amazon bloqueia IPs de datacenter com frequência |
| Shopee | Endpoint interno da busca | Instável — Shopee tem proteção anti-bot forte |

Isso não foi testado ao vivo antes da entrega (ambiente de desenvolvimento
sem acesso a esses sites). É esperado que Kabum/Terabyte precisem de um
pequeno ajuste de seletor CSS e que Amazon/Shopee falhem em algumas execuções
— quando isso acontece, o site simplesmente não entra na comparação daquela
rodada (não quebra o script inteiro).

### Como corrigir um scraper que parou de funcionar

1. Rode manualmente (**Run workflow**) e olhe o log — ele imprime quantos
   resultados cada site retornou.
2. Se um site voltar com 0 resultados, o layout do HTML provavelmente mudou.
3. Abra o site no navegador, aperte **F12 → inspecionar** em um card de
   produto, veja a classe/estrutura atual, e me envie esse trecho de HTML —
   eu ajusto o seletor no `price_monitor.py` rapidinho.

---

## Arquivos

- `price_monitor.py` — script principal
- `config.json` — preço-alvo e sites ativos
- `state.json` — histórico (atualizado automaticamente a cada execução)
- `requirements.txt` — dependências Python
- `.github/workflows/monitor.yml` — agendamento na nuvem
