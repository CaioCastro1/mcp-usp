
var carregouProjetoPedagogico = false, carregouGradeCurricular = false;
var numseqprjpeg, dtainiprjpeg;

$(function() {
	$("#tabs").tabs({
		disabled: [1, 2, 3],
		select: function(evt, ui) {
			if ($(ui.tab).attr('href') == "#step1") {
				setTimeout(function() {
					$("#tabs").tabs("disable", 1);
					$("#tabs").tabs("disable", 2);
					$("#tabs").tabs("disable", 3);
				}, 10);
			} else if ($(ui.tab).attr('href') == "#step3") {
				if (!carregouProjetoPedagogico) {
					$("#documento").attr("src", "");
					mostrarMensagemAguardar();
					CursoControlePublicoDWR.recuperarProjetoPedagogico($("#comboCurso").val().split("|")[0], numseqprjpeg, dtainiprjpeg, function(url) {
						desbloquearTela();
						$("#documento").attr("src", url + "?disposition=inline");
						carregouProjetoPedagogico = true;
					});
				}
			} else if ($(ui.tab).attr("href") == "#step4") {
				if (!carregouGradeCurricular) {
					$("#gradeCurricular").empty();
					mostrarMensagemAguardar();
					ControlePublicoDWR.listar("pubGradeCurricular", {codcur: $("#comboCurso").val().split("|")[0], codhab: $("#comboCurso").val().split("|")[1], tipo: "N"}, function(lista) {
						var numsemidl = 0;
						var tipobg = "";
						for (var i in lista) {
							if (lista[i].tipobg != tipobg) {
								var texto = "";
								if (lista[i].tipobg == "O") {
									texto = "Disciplinas ObrigatÃ³rias";
								} else if (lista[i].tipobg == "C") {
									texto = "Disciplinas Optativas Eletivas";
								} else {
									texto = "Disciplinas Optativas Livres";
								}
								if (tipobg != "") {
									$("<br>").appendTo("#gradeCurricular");
								}
								$("<table>").css("width", "100%").appendTo("#gradeCurricular");
								$("<tr>").css({"background-color": "#1094AB", "color": "white"}).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold"}).attr("colspan", "8").html(texto)
								).appendTo("#gradeCurricular table:last");
								numsemidl = 0;
							}
							if (lista[i].numsemidl != numsemidl) {
								$("<tr>").css({"background-color": "#cccccc"}).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold"}).attr("colspan", "2").html(lista[i].numsemidl + "Âº Semestre Ideal")
								).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold", "text-align": "center"}).html("CrÃ©d. Aula")
								).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold", "text-align": "center"}).html("CrÃ©d. Trab.")
								).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold", "text-align": "center"}).html("CH")
								).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold", "text-align": "center"}).html("CE")
								).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold", "text-align": "center"}).html("CP")
								).append(
									$("<td>").css({"padding": "5px", "font-weight": "bold", "text-align": "center"}).html("ATPA")
								).appendTo("#gradeCurricular table:last");
							}
							$("<tr>").css("height", "20px").append(
								$("<td>").css("width", "100px").append($("<a>").attr("href", "#").attr("data-coddis", lista[i].coddis).addClass("disciplina").html(lista[i].coddis))
							).append(
								$("<td>").html(lista[i].nomdis)
							).append(
								$("<td>").css("width", "100px").css("text-align", "right").css("padding-right", "5px").html(lista[i].creaul)
							).append(
								$("<td>").css("width", "100px").css("text-align", "right").css("padding-right", "5px").html(lista[i].cretrb)
							).append(
								$("<td>").css("width", "100px").css("text-align", "right").css("padding-right", "5px").html(15 * parseInt(lista[i].creaul, 10) + 30 * parseInt(lista[i].cretrb, 10))
							).append(
								$("<td>").css("width", "100px").css("text-align", "right").css("padding-right", "5px").html(lista[i].cgahoreto)
							).append(
								$("<td>").css("width", "100px").css("text-align", "right").css("padding-right", "5px").html(lista[i].cgahorlcn)
							).append(
								$("<td>").css("width", "100px").css("text-align", "right").css("padding-right", "5px").html(lista[i].cgaacdciecul)
							).appendTo("#gradeCurricular table:last");
							tipobg = lista[i].tipobg;
							numsemidl = lista[i].numsemidl;
							$("<tr>").css("color", "#EB8F00").addClass("dis" + lista[i].coddis).append(
								$("<td>").attr("colspan", "8").html("Carregando requisitos...")
							).appendTo("#gradeCurricular table:last");
							ControlePublicoDWR.listar("pubListarRequisitoDisciplina", {codcur: $("#comboCurso").val().split("|")[0], codhab: $("#comboCurso").val().split("|")[1], coddis: lista[i].coddis}, {
								arg: lista[i].coddis,
								callback: function(requisitos, disciplina) {
									for (var i in requisitos) {
										$("<tr>").css("color", "#EB8F00").append(
											$("<td>").css("padding-left", "25px").attr("colspan", "2").html(requisitos[i].coddisreq + " - " + requisitos[i].nomdisreq)
										).append(
											$("<td>").attr("colspan", "6").html(requisitos[i].tipreq == "PR" ? (requisitos[i].stamtrrcp == "S" ? "Requisito fraco" : "Requisito") : "IndicaÃ§Ã£o de conjunto")
										).insertBefore(".dis" + disciplina);
									}
									$(".dis" + disciplina).remove();
								}
							});
						}
						ControlePublicoDWR.obter("pubObterInfoCursoWeb", {codcur: $("#comboCurso").val().split("|")[0], codhab: $("#comboCurso").val().split("|")[1], tipo: "N"}, function(data) {
							let obscrl = data.obscrl || "";
							if (obscrl = $("<div>").html(obscrl).text()) {obscrl = obscrl.replace(/\n/g, "<br>");}
							$(".informacoesEspecificas").html(obscrl);
							desbloquearTela();
							carregouGradeCurricular = true;
						});
					});
				}
			}
	    }
	});
	$("#disciplinaDialog").dialog({
		modal: true,
		width: 800,
		height: 600,
		autoOpen: false
	});
	$("#limpar").button().click(function() {
		$("#comboUnidade, #comboCurso").val("");
	});
	$("#enviar").button().click(function() {
		if ($("#form1").validationEngine("validate")) {
			mostrarMensagemAguardar();
			$(".curso").html($("#comboCurso option:selected").html());
			$(".unidade").html($("#comboUnidade option[value=" + Math.floor(parseInt($("#comboCurso").val().split("|")[0], 10) / 1000) + "]").html());
			ControlePublicoDWR.obter("pubObterInfoCurso", {"codcur": $("#comboCurso").val().split("|")[0], "codhab": $("#comboCurso").val().split("|")[1]}, function(lista) {
				desbloquearTela();
				if (lista.numseqprjpeg) {
					numseqprjpeg = lista.numseqprjpeg;
					dtainiprjpeg = lista.dtainiprjpeg;
					$(".dataInicio").html(lista.dtainiprjpeg);
					$(".dataFim").html(lista.dtafimprjpeg);
					$(".duridlhab").html(lista.duridlhab);
					$(".durminhab").html(lista.durminhab);
					$(".durmaxhab").html(lista.durmaxhab);
					$(".descricaoPerfilAluno").html(lista.dscprfalugrd);
					$(".objetivos").html(lista.objcur);
					$(".competencias").html(lista.ctchblcur);
					$(".informacoes").html(lista.outifmcur);
					$('#tabs').tabs('enable', 1);
					$('#tabs').tabs('enable', 2);
					$('#tabs').tabs('enable', 3);
					$('#tabs').tabs('select', 1);	
					carregouProjetoPedagogico = false;
					carregouGradeCurricular = false;					
				} else {
					mostrarErroModal("Dados nÃ£o encontrados!");
				}
			});
		}
	});
	ControlePublicoDWR.listar("pubListarColegiado", {"pfxdisval": "XXX", "codcg": "0"}, function(lista) {
		dwr.util.addOptions("comboUnidade", lista, "codclg", function(item) {
			return item.nomclg;
		});
	});
	$("#comboUnidade").change(function() {
		dwr.util.removeAllOptions("comboCurso");
		dwr.util.addOptions("comboCurso", {"": ""});
		if ($("#comboUnidade").val() != "") {
			ControlePublicoDWR.listar("pubListarCursoEntrada", {"codclg": $("#comboUnidade").val()}, function(lista) {
				dwr.util.addOptions("comboCurso", lista, function(item) {
					return item.codcur + "|" + item.codhab;
				}, function(item) {
					if (item.nomhab == item.nomcur) {
						return item.nomcur + " - " + item.perhab;
					}
					return item.nomcur + " (" + item.nomhab.replace(item.nomcur + " - ", "").replace(item.nomcur, "") + ") - " + item.perhab;
				});
			});
		}
	}).change();
	$("#gradeCurricular").on("click", ".disciplina", function() {
		mostrarMensagemAguardar();
		var coddis = $(this).attr("data-coddis");
		ControlePublicoDWR.obter("pubObterDisciplina", {coddis: $(this).attr("data-coddis"), verdis: 0}, function(data) {
			var cargaHorariaTotal = "";
			if (data.cgahoreto != 0) {
				cargaHorariaTotal += ", EstÃ¡gio: " + data.cgahoreto + " h";
			}
			if (data.cgahorlcn != 0) {
				cargaHorariaTotal += ", PrÃ¡ticas como Componentes Curriculares: " + data.cgahorlcn + " h";
			}
			if (data.cgaacdciecul != 0) {
				cargaHorariaTotal += ", Atividades AcadÃªmico-CientÃ­fico-Culturais: " + data.cgaacdciecul +  " h";
			}
			var tipo = "";
			if (data.tipdis == "A") {
				tipo = "Anual";
			} else if (data.tipdis = "S") {
				tipo = "Semestral";
			} else if (data.tipdis = "Q") {
				tipo = "Quadrimestral";
			}
			$("#disciplinaDialog")
					.find(".creditosAula").html(data.creaul).end()
					.find(".creditosTrabalho").html(data.cretrb).end()
					.find(".cargaHorariaTotal").html((data.creaul * 15 + data.cretrb * 30) + " h" + (cargaHorariaTotal != "" ? ("(" + cargaHorariaTotal.substring(1) + ")") : "")).end()
					.find(".tipo").html(tipo).end()
					.find(".ativacao").html(data.dtaatvdis).end()
					.find(".objetivos").html(data.objdis).end()
					.find(".programaResumido").html(data.pgmrsudis).end()
					.find(".programa").html(data.pgmdis).end()
					.find(".metodoAvaliacao").html(data.dscmtdavl).end()
					.find(".criterioAvaliacao").html(data.crtavl).end()
					.find(".normaRecuperacao").html(data.dscnorrcp).end()
					.find(".bibliografia").html(data.dscbbgdis).end();
			ControlePublicoDWR.listar("pubListarDiscipResp", {coddis: coddis}, function(lista) {
				desbloquearTela();
				$("#disciplinaDialog").find(".docentesResponsaveis").empty();
				for (var i in lista) {
					$("<li>").html(lista[i].codpes + " - " + lista[i].nompes).appendTo($("#disciplinaDialog").find(".docentesResponsaveis"));
				}
				$("#disciplinaDialog").dialog("option", "title", data.coddis + " - " + data.nomdis).dialog("open");
			});
		});
		return false;
	});
});
