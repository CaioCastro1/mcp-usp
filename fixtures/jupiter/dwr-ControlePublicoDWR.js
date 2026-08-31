if (typeof dwr == 'undefined' || dwr.engine == undefined) throw new Error('You must include DWR engine before including this file');

(function() {
if (dwr.engine._getObject("ControlePublicoDWR") == undefined) {
var p;

p = {};







p.executarBatch = function(p0, p1, p2, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'executarBatch', arguments);
};







p.executar = function(p0, p1, p2, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'executar', arguments);
};






p.obterArquivo = function(p0, p1, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterArquivo', arguments);
};







p.listar = function(p0, p1, p2, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'listar', arguments);
};







p.obter = function(p0, p1, p2, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obter', arguments);
};






p.obterRelatorio = function(p0, p1, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterRelatorio', arguments);
};






p.obterCsv = function(p0, p1, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterCsv', arguments);
};






p.obterPdf = function(p0, p1, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterPdf', arguments);
};






p.obterZip = function(p0, p1, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterZip', arguments);
};






p.obterWebdoc = function(p0, p1, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterWebdoc', arguments);
};





p.obterProgresso = function(p0, callback) {
return dwr.engine._execute(p._path, 'ControlePublicoDWR', 'obterProgresso', arguments);
};

dwr.engine._setObject("ControlePublicoDWR", p);
}
})();

