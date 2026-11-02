# Pesquisa — Sequências de Acordes Customizadas

## Perguntas a responder

1. **Algoritmo de matching**: hoje, as 6 sequências hardcoded em `main.py` (linhas
   40-45) são comparadas contra músicas via uma tag pré-computada
   (`SEQ_FAMOSA`/`seqs_famosas`, vinda do CSV). Sequências cadastradas pelo usuário
   não têm essa tag — o matching precisa ser calculado em tempo real a partir da
   lista de acordes de cada música (`musica.acordes`/`musica.cifra`). O que vai
   definir "a sequência X aparece na música Y"? A ordem dos acordes importa?
   Repetições de acorde dentro da música importam? É preciso normalizar (ex.:
   maiúsculas/minúsculas, variações de escrita do mesmo acorde)?
2. **Validação da hipótese**: rode o algoritmo que você está considerando contra os
   dados reais em `data/top/dataset_final.csv`, para as 6 sequências hoje
   hardcoded, e confirme (ou refute) que ele reproduz os mesmos matches que o
   código atual produz via `seqs_famosas`. Esse é o bar mínimo de correção que
   você vai usar na fase de testes.
3. **Banco de dados**: quais bancos embarcados (sem serviço externo adicional) são
   viáveis dentro do container Docker único e local-only já documentado em
   `docs/adr/0001-local-only-docker-deploy.md`? O que cada opção implica para o
   `Dockerfile` atual e para a persistência dos dados entre reinícios do
   container?
4. **Frontend existente**: o que a página `#/porsequencia`
   (`static/templates/sequencia.html` +
   `static/assets/js/controllers/sequencia.js`) já faz? Repare que ela tem hoje uma
   lista *hardcoded no JavaScript* de 4 sequências (`sequencia1`..`sequencia4`),
   diferente das 6 que existem no backend — um detalhe real e pré-existente do
   código, não um erro seu, que vale entender antes de decidir o que precisa
   mudar.

## Registro das descobertas

1. Após rodar a skill de research-codebase, comecei a ler o arquivo `codebase-overview.md` gerado pela skill, buscando entedem sobre o projeto no geral e ja tentar encontrar algumas respostas para as perguntas sugeridas na atividade. 

Um dos primeiros pontos que me chamaram atenção foi que nas linhas 17 e 18 do `codebase-overview` o modelo descreveu uma das features do sistema como 'chord/sequence similarity over unique chord sets'. Achei que entender melhor essa feature seria um bom primeiro passo para pensar no algoritmo de matching da nova feature. Por isso, comecei a conversar com o agente para que ele descrevesse melhor essa feature da similaridade por acordes. 
Após as primeira interações entendendo melhor a feature no chat com o modelo e analisando o código em pontos que ele sugeriu(principalmente o algorito de get_similares() que ja faz um matching com acordes), cheguei a conclusão que de fato essa feature eh relevante para pensar na nova feature, porque posso utilizar uma ideia parecida de encontrar uma interseçao das musicas baseada nos acordes das novas sequencias famosas criadas e os própios acordes que temos no csv. A primeira diferença que vem a minha mente é que o /similares quando eh executado para acordes, funciona com sets, que muda a ordem dos acordes da música e remove repetições, duas coisas que são problemas para a feature pensanda para criar novas sequencias famosas que podem conter repetição e precisam preservar a ordem.
Relendo a primeira pergunta, de fato: Ordem importa e repetições de acorde importa.
* Nesse ponto, pedi para que o modelo rodasse o projeto para que eu entendesse como as features funcionam em tela, alog que não havia feito ainda.
* Rodar o projeto foi importante para perceber uma coisa:
   *  Já eh apresentada a lista de acordes individuais que o usuário pode utilizar para montar a sequencia, ou seja, eu não preciso me preocupar em normalizar oque esta sendo recebido do usuário. Isso já responde a última pergun da questão 1. Acredito que não devo normalizar os acordes. Uma outra pergunta que fiz ao modelo foi justamente se já existe alguma normalização sendo feita dos acordes que vem do CSV e ele me apontou que não, so eram feitas limpezas sobre a cifra pura do csv, mas nenhuma normalização sobre os acordes em si.
* Acabei ficando com outra dúvida nesse ponto que foi a difença entre cifra e acordes no projeto. E comecei a conversar com o modelo sobre essa diferença. Descobri que certamente oque utilizarei para dar match com as novas sequencias famosas será a cifra. A cifra ja contem os acordes em uma lista python na mesma ordem que aparecem no csv e por não estar em um set, também preserva as repetições. 
* Minha principal dúvida no momento eh: O algoritmo para percorrer e encontrar interseções dessa maneira, considerando todos os acordes da música, é Nˆ2? Isso eh um problema para a solução? Vamos precisar calcular as interseções em tempo de execução, quando o usuário selecionar a sequencia? Uma das limitações da atividade foi não migrar as músicas para o banco  "So o catalogo de sequencias precisa de persistencia" com isso, acredito que eu não posso computar as interseçoes apenas quando o usuário cria-la e salvar os id_musica. Vou seguir com a ideia de realizar a computação sempre que o usuário selecionar a sequencia. 
* Um ponto de melhoria que pensei durante a leitura do `codebase-overview.md` eh que na documentançao do RePIT eh sugerido que utilize-se o Research antes de cada feature nova que vai ser implementada, criando/atualizando a documentação com novas mudanças que podem ter acontecido na codebse. O ponto um pouco ruim eh que a skill gera uma avaliação completa sobre o sistema e isso eh bem últi quando estamos lidando com um sistema novo, porém, tambem tras um lado negativo, o codebase-overview.md tenta falar sobre tudo do sistema e ao mesmo tempo, então eh difícil entender qual parte do documento ler para encontrar algo que tenha relação com oque estamos tentando implmentar, talvez fizesse mais sentido focar o research ja na feature que estamos buscando implementar, ou ter uma skill alternativa `research-feat`, nao sei. 
* Eu mesmo não notei que no documento já tinha um trecho falando sobre o funcionamento do /similares. Foi falta de atenção com uma dose de querer implementar/entender a nova feature rápido. O correto talvez fosse ler o codebase-overview completamente, com mais atenção, antes de fazer qualquer outra coisa, mas isso tem justemente a dificuldade de ser um arquivo enorme, para um sistema que nem parece ser tão grande assim.

2. Para resolver esse segunda pergunta eu utilizei novamente o modelo para criar um arquivo de teste. Não codei o algoritmo na mão. Descrevi o algoritmo de match com o máximo de detalhes que consegui pensar e pedi que o model implementasse utilizando o get_similaridade() como base, porque, na minha cabeça os dois algoritmos fariam coisa bem parecida.
* Na premeira rodada desse arquivo de teste gerado pelo modelo o resultado foi diferente das músicas retornadas para a sequencia pre computada. A primeira coisa que veio a mente foi tentar entender se alguma música com a tag precomputada estava faltando no retorno, porque se a divergencia fossem músicas a mais, pode ser que o algoritmo esteja funcionando e algumas músicas que contem sequencia válida, não possuem a tag.
* Analisando o arquivo `test_order_preserving_match.py` que foi o arquivo criado pelo modelo para validar a ideia do meu algoritmo, econtrei um problema, na descriçao da funçao que o modelo criou para validar o match, temos o seguinte: `Retorna True se todos os acordes de target aparecem na ordem em que foram passados, possivelmente com outros acordes no meio.` Linhas 59 e 60 do arquivo. A forma que expliquei o algoritmo para o modelo deu a entender que nao me importaria com acordes no meio, mas acredito que nao podemos ter esses acordes no meio para ser de fato uma sequencia. 
* Pedi para que ele corrigisse esse algoritmo para mais uma vez, tentar validar a ideia do algoritmo com as musicas com tags que ja existem. 
* Analisando essa nova versão do algoritmo que o ageten gerou, percebi que eh um for bem simples, comparando sub arrays do array de cifras da música com a sequencia alvo e para mim, faz todo sentido que seja assim. MEsmo assim, o novo algoritmo encontra mais músicas, por isso, pedi para que o agente me apontasse uma musica que esta sendo capturada apenas pelo novo algoritmo para que eu analise se esta fazendo sentido o match. 
* Analisei a música `Victor e Leo - Fotos (victor-leo_fotos)` que se enquadra na seq `CGAmF` e de fato ela nao possue a tag, mas pela minha analise, faz todo sentido que a musica de match. Por isso, acredito que as tags pre computadas possuem alguns gaps e acredito que consegui validar uma versão boa do algoritmo que se encontra em `test_order_preserving_match.py`. 

3.Sobre essa pergunta, já tinha um banco em mente: SQLite, ja tenho noçao tecnica que ele funciona para o cenário que estamos utilizando e com as restrições apresentadas. Então, decide apenas analisar essa possibilidade com o agente, para confirmar minha hipótese ou levantar algum problema que eu não esteja vendo. 
* Usei o modelo para me explicar melhor os problemas relatados em `001-local-only-docker-deploy.md`, nao tinha entendido completamente. Após a conversa entendi com clareza que foram apenas removidas antigas configs de deploy obesoletas e tenho confiança que o SQLite funcionaria no nosso cenário,  o agente não me apresentou nnenhum ponto que eu já não conhecesse. 

4.Analisando manualmente o arquivo do front, de fato, so estão mapeadas as sequências: 0,1,4,5.  Nao sei explicar porque apenas essas 4 estão mapeadas. 
* Um ponto relevante sobre o processo nessa questão 4 foi que ao tentar analisar o `static/templates/sequencia.html` percebi que eu lembrava bem pouco sobre como funciona angular e foi a primeira vez que me deu vontade de voltar a analisar o `codebase-overview.md`, então, para mim essa analise geral, funciona bem mais como algo últil para consultar esporadicamente do que como um arquivo muito útil para introduzir o sistema. De fato, ao voltar a ler o arquivo na parte de frontend, percebi que ele ja falava algumas das coisas que tinha reparado, como o fato de so terem 4 sequencias mapeadas... 
* Algo que reparei nesse momento, analisando os artefatos de front gerados no `codebase-overview.md` eh que não eh algo voltado para explicar o funcionamento do angular em si, a spec não vai se atentar a detalhes como as tags `ng-click` utilizadas dentro do html especificas do angular que renderizam as sequencias clicáveis no front. Mas a spec gera um overview com um nível de detalhes legal,  informando onde estão as linhas que executa cada etapa importante no fluxo da funcionalidade de sequencia e meio que cabe ao engenheiro apronfundar no funcionamento da coisas, se necessário. 
* No fim, acredito que analisar essa pergunta me fez perceber que preciso fazer o request pro banco para mapear as sequencias ja existentes toda vez que acessarmos a tela, algo que eu não havia pensado ainda. 


## Trade-offs identificados

* Acredito que nesse ponto do desenvolvimento eu não enxerguei trade-offs claros ainda. A forma de implementar parece bem natural e alinhada com oque eu estou pensando desde o começo e não consegui enxergar pontos que inviabilisem as ideias que tenho no momento, não sei se isso reflete uma fase de analise fraca, ou uma dependência minha para com o agente para identificar trade-offs.
