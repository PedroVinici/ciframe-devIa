# Proposta — Sequências de Acordes Customizadas

## Abordagem escolhida

* A primeira proposta que o modelo sugeriu ao utilizar a skill ja me agradou bastante. Senti falta apenas de algo relacionado a criação de um volume no container para garantir a persistencia entre reinicios da aplicação.
* Algo que nenhuma das propostas me perguntou foi sobre como receber o input do usuário em tela, a primeira apenas afirmou: `add a simple "Cadastrar nova sequência" form (POST to new endpoint)` . Ou seja, nenhum detalhe sobre como o usuário vai montar a sequencia a ser cadastrada. Para isso eu ja tinha a ideia de copiar exatamente a tela de busca por acordes /similares. 
* A segunda sugestão do modelo foi interessante, era algo que eu já tinha pensado que seria guardar tanto as sequencias em banco quanto os ids de musicas que derem match nessas sequencias no moemento da persistencia. Obiviamente isso quebra a regra da atividade de persistir em banco apenas as sequencias e isso foi uma coisa que eu informei ao modelo no prompt da proposição da feature (`Só o catálogo de sequências precisa de persistência`) e mesmo assim, ele sugeriu essa opção... Essa solução, provavelmente foi a que o agente pensou para resolver o principal trade-off que ele percebeu da primeira solução, que foi a questão de performance no cenário de precisar realizar a busca completa pelos matchs. E de fato, eh uma solução mais elegante, porém, fere uma regra que passei pra ele.
* Indiquei alguns ajuste na proposta 1 e pedi um detalhamento sobre como se dará a config docker, especificando o uso de um volume.  
### Algoritmo de matching

* Segui com a ideia de `cifra[i : i+len] == target` que apereceu como sugestão das duas propostas provavelmente por ser algo que já havia conversado com o modelo. 

### Banco de dados

* SQLite, porque foi a sugestão original que fiz ao agente e ele não econtrou nenhum ponto contra a utilização. 
* Outro ponto relevante sobre o banco que não havia pensado e apareceu na proposta 1, eh a questão de como alimentar o back com as novas sequencias. A sugestão foi fazer da mesma forma que esta sendo feito hoje com o CSV das músicas, que eh upado pro back no inicio da aplicação. No entanto, acredito que essa não eh uma forma inteligente de utilizar um banco que eh claramente diferente dos CSVs, nao vejo vantagens em upar todas as sequencias cadastradas para o back como eh feito com as musicas, porque claramente isso eh feito com as musicas, pela dificuldade que existe em ler um csv daí, escolhesse ler apenas uma vez. Ja no caso do banco eh bem mais facil recupear a sequencia apenas no momento de envia-las para o front, nao precisamos mante-las em memnoria. Vou corrigir isso na proposta 1 do modelo.
* Uma pergunta relevante que o agente fez na proposta 1: `Conflict resolution: How to handle duplicate sequences (same ordered list)? Reject, merge, or return existing id?`. Respondi que conflitos impedem a criação da sequencia. 

### Esquema de dados (alto nível)

* Apenas a tabela de sequencia. Com ID e a propia sequencia em formato de texto normalizado. 

### API

* Isso não foi especificado em nenhuma proposta gerada pela skill. Acredito que o ideal eh criar um novo endpoint e não utilizar o /similares, ja que vamos precisar que seja um endpoint POST e GET.

### Frontend
* Na tinha pensado no fluxo todo do front até chegar nessa pergunta, então, após pensar em mais detalhes como está abaixo, acidionei como uma nova alteração na proposta 1 do agente. 
* No front muda que teremos uma nova tela acessivel a partir de `#porsequencia`, `#cadastra-seqfamosa` com um "form" preenchido com a mesma UI que existe para a escolha dos acorde em `#poracorde` e apos a inserção essa sequence o usuário eh redirecionado para a tela `#porsequencia`ja atualiza com musicas filtradas pela nova sequencia cadastrada, na mesma tela com sequencias na esquerda e musicas na diretia, como ja aconetce hoej.
* Também defini que todas as sequencias serão buscadas pela nova feature, parando de utilizar o match de campo do csv.

## Alternativas consideradas e descartadas

* Justamente a proposta 2, que teria uma performace claremente melhor ao persistir as sequencias junto com os ids das musicas que deram match, porém, ferem a regra de utilizar o banco apenas para as sequencias.

## Escopo explícito


**Dentro do escopo:**

- Precisei pedir para que ele inserisse as 6 sequencias que existem hoje no banco no momento de criação da tabela de sequencia, isso não estava previsto na proposta. 

**Fora do escopo (e por quê):**

- O modelo sugeri incluir colunas TIMESTAMP e NOME para as sequencias. Acredito que os dois estão fora do scop e não são necessarios na feature. 


***OBS: Acredito que tive um Overusing dessa skill de proposta. Senti que a ideia dela era muito mais entregar uma ideia bem enxuta sobre a implementação para que passassemos mais tempo ajustando o plano na proxima skill após escolher uma linha base de como seguir, porém, como eu já entreguei uma feature bem estruturada para a skill de proposta, as duas propostas sugeridas não tinha muita diferença, a única seria fazer o match em tempo de execuçao, ou pre computar o match. Então, como a própia atividade ja veio desde o research, induzindo a pensar em cada detalhe a implementação, acredito que a contribuição da /make-proposal foi baixa, a principal foi abrir um pouco mais os olhos sobre a nao necessidade de manter as sequencias em memoria e como lidar com duplicatas nas sequencias.***
***OBS: Como a `/make-proposal` nao gera arquivos, nao utilizei o compact antes de chamar o `/make-plan` para nao perdem nada do contexto e das atualizassoes que pedi para o agent sobre a propsta***