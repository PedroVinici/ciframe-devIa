angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, GENEROS) {
  var COR_SEQUENCIA = '#2E1C74';
  var vm = this;
  vm.sequenciasFamosas = [];
  vm.minhaSequencia = { acordes: [] };
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  var toTemplateSequence = function(sequencia) {
    return {
      'id': sequencia.id,
      'acordes': sequencia.acordes.map(function(acorde) {
        return { 'acorde': acorde, 'cor': COR_SEQUENCIA };
      })
    };
  }

  var selecionarSequenciaDaUrl = function() {
    var id = $location.search().id;
    if (id === undefined || id === null || id === '') {
      return;
    }
    for (var i = 0; i < vm.sequenciasFamosas.length; i++) {
      if (String(vm.sequenciasFamosas[i].id) === String(id)) {
        vm.pesquisarPorSequencia(vm.sequenciasFamosas[i]);
        return;
      }
    }
  }

  var carregarSequencias = function() {
    $http.get('sequencias')
      .success(function(data) {
        vm.sequenciasFamosas = data.map(toTemplateSequence);
        selecionarSequenciaDaUrl();
      })
      .error(function(data) {
        vm.esfigeSpeech = "Ops! Algo errado.";
      });
  }

  vm.temAcorde = function(acordeon) {
    if (vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acordeon) > -1);
    }
    return false;
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    if (!vm.minhaSequencia || vm.minhaSequencia.id === undefined || vm.minhaSequencia.id === null) {
      return;
    }
    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.musics = [];

    var searchString = "similares?sequencia_id=".concat(vm.minhaSequencia.id);
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos=" + encodeURIComponent(vm.meuGenero);
    }
    $http.get(searchString)
      .success(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = data;
      })
      .error(function(data) {
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  vm.limparPesquisa = function() {
    vm.minhaSequencia = { acordes: [] };
    vm.musics = [];
    $location.search('id', null);
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };

  carregarSequencias();
});
