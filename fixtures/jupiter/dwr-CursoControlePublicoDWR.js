if (typeof dwr == 'undefined' || dwr.engine == undefined) throw new Error('You must include DWR engine before including this file');

(function() {
if (dwr.engine._getObject("CursoControlePublicoDWR") == undefined) {
var p;

p = {};







p.recuperarProjetoPedagogico = function(p0, p1, p2, callback) {
return dwr.engine._execute(p._path, 'CursoControlePublicoDWR', 'recuperarProjetoPedagogico', arguments);
};

dwr.engine._setObject("CursoControlePublicoDWR", p);
}
})();

