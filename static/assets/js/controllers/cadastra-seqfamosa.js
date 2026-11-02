angular.module('deciframeApp').controller('CadastraSequenciaController', function($http, $location) {
  var acordesC = [
    { 'acorde': 'C',  'cor': '#e6b300' },
    { 'acorde': 'C#', 'cor': '#e6b300' },
    { 'acorde': 'Cm', 'cor': '#efcc59' },
    { 'acorde': 'C#m','cor': '#efcc59' },
    { 'acorde': 'C7', 'cor': '#d6a602' },
    { 'acorde': 'C#7','cor': '#d6a602' }];
  var acordesD = [
    { 'acorde': 'D',  'cor': '#cb6018' },
    { 'acorde': 'D#', 'cor': '#cb6018' },
    { 'acorde': 'Dm', 'cor': '#cf6f3e' },
    { 'acorde': 'D#m','cor': '#cf6f3e' },
    { 'acorde': 'D7', 'cor': '#bc5a1d' },
    { 'acorde': 'D#7','cor': '#bc5a1d' }];
  var acordesE = [
    { 'acorde': 'E',  'cor': '#b72c52' },
    { 'acorde': 'Em', 'cor': '#c5516e' },
    { 'acorde': 'E7', 'cor': '#a92f4d' }];
  var acordesF = [
    { 'acorde': 'F',  'cor': '#ba007c' },
    { 'acorde': 'F#', 'cor': '#ba007c' },
    { 'acorde': 'Fm', 'cor': '#c02a88' },
    { 'acorde': 'F#m','cor': '#c02a88' },
    { 'acorde': 'F7', 'cor': '#ad0076' },
    { 'acorde': 'F#7','cor': '#ad0076' }];
  var acordesG = [
    { 'acorde': 'G',  'cor': '#7b057e' },
    { 'acorde': 'G#', 'cor': '#7b057e' },
    { 'acorde': 'Gm', 'cor': '#882888' },
    { 'acorde': 'G#m','cor': '#882888' },
    { 'acorde': 'G7', 'cor': '#710c77' },
    { 'acorde': 'G#7','cor': '#710c77' }];
  var acordesA = [
    { 'acorde': 'A',  'cor': '#76aadb' },
    { 'acorde': 'A#', 'cor': '#76aadb' },
    { 'acorde': 'Am', 'cor': '#89c0e9' },
    { 'acorde': 'A#m','cor': '#89c0e9' },
    { 'acorde': 'A7', 'cor': '#6c9ecc' },
    { 'acorde': 'A#7','cor': '#6c9ecc' }];
  var acordesB = [
    { 'acorde': 'B',  'cor': '#a3bd31' },
    { 'acorde': 'Bm', 'cor': '#cdd54f' },
    { 'acorde': 'B7', 'cor': '#96b02f' }];

  var vm = this;
  vm.acordes = [];
  vm.acordes.push(acordesC);
  vm.acordes.push(acordesD);
  vm.acordes.push(acordesE);
  vm.acordes.push(acordesF);
  vm.acordes.push(acordesG);
  vm.acordes.push(acordesA);
  vm.acordes.push(acordesB);
  vm.minhaSequencia = [];
  vm.erro = "";
  vm.salvando = false;

  vm.addAcorde = function(acordeon) {
    var index = vm.minhaSequencia.indexOf(acordeon);
    if (index == -1) {
      vm.minhaSequencia.push(acordeon);
    } else {
      vm.minhaSequencia.splice(index, 1);
    }
    vm.erro = "";
  }

  vm.temAcorde = function(acordeon) {
    return (vm.minhaSequencia.indexOf(acordeon) > -1);
  }

  vm.limpar = function() {
    vm.minhaSequencia = [];
    vm.erro = "";
  }

  vm.cadastrar = function() {
    if (!vm.minhaSequencia.length || vm.salvando) {
      return;
    }

    var acordes = vm.minhaSequencia.map(function(acordeon) {
      return acordeon.acorde;
    });

    vm.salvando = true;
    vm.erro = "";

    $http.post('sequencias', { 'acordes': acordes })
      .success(function(data) {
        vm.salvando = false;
        $location.path('/porsequencia').search('id', data.id);
      })
      .error(function(data) {
        vm.salvando = false;
        if (data && data.erro) {
          vm.erro = data.erro;
        } else {
          vm.erro = "Ops! Algo errado.";
        }
      });
  }
});
