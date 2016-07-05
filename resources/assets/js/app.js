$.ajaxSetup({ cache: false });
var structure = {"name": "Palantir",
                 "rows": [],
                 "columns": []
                 }

function loadjson(filepath, callback) {
  console.log("Attempting to load "+filepath)
  setTimeout(function() {
    $.ajax({ url: filepath,
      success: function(data) {
        callback(data)
      }, dataType: "json",
      error: function(data) {
        callback()
        //console.log("Error!", data);
      }
    });
  }, 100);
}

function addmodal(data) {
  if (!data) {
    data = {'ModalTitle': "Under Construction", 'ModalContent': 'None'}
  };
  $("#modalcontent").processTemplate(data);
  $('#modalcontent').modal('show')
}

function addcontent(data) {
  if (!data) {
    console.error("404 Not Found")
  } else {
    templatecontents["contents"] = data
    $("#bodycontent").processTemplate(templatecontents);
    $('pre').each(function(i, block) {
        hljs.highlightBlock(block);
    });
  }
}

function loadmodal(id) {
  console.log("Loading cell "+id);
  $("#modalcontent").setTemplateURL("templates/modalcontent.html", { filter_data: false });
  loadjson("data/" + id + ".json", addmodal);
}

function update_cell(data) {
  if (!data) {
    console.error("404 Not Found")
  } else {
    cell = document.getElementById(data.id)
    cell.style.cssText = "color: "+data.color+"; background-color: "+data.bgcolor
    cellclass = "statuscell"
    if (data.animation != "none") {
      cellclass += " statuscell-"+data.animation
    }
    cell.className = cellclass
    cell.innerHTML = data.text
  }
}

function generate(data) {
  if (!data) {
    console.error("404 Not Found");
  } else {
    if (JSON.stringify(data) !== JSON.stringify(structure) || data.rows.length == 0 || data.cols.length == 0) {
      console.log("Updating structure")
      titleElement = document.getElementById("title");
      titleElement.innerHTML = "Palantir | " + data["name"];
      navtitleElement = document.getElementById("navbartitle");
      navtitleElement.innerHTML = data["name"];
      if (data.rows.length == 0 || data.cols.length == 0) {
        noticeElement = document.getElementById('notice');
        noticeElement.innerHTML = '<div class="alert alert-warning" role="alert">There is nothing to show! Add columns or rows to get started!</div>'
        tableElement = document.getElementById('table');
        tableElement.innerHTML = "";
      } else {
        noticeElement = document.getElementById('notice');
        noticeElement.innerHTML = ''
        table = '<tr><th id="column_headers" class="statuscell text-center darker"></th>';
        for (c = 0; c < data.cols.length; c++) {
          table = table += '<th class="statuscell text-center darker" title="ID: {%%COLUMN_ID%%}">{%%COLUMN_NAME%%}</th>'.replace("{%%COLUMN_ID%%}", data.cols[c].id).replace("{%%COLUMN_NAME%%}", data.cols[c].text)
        }
        table += "</tr>";
        for (r = 0; r < data.rows.length; r++) {
          table += '<tr><th class="statuscell text-center darker" title="ID: {%%ROW_ID%%}">{%%ROW_NAME%%}</th>'.replace("{%%ROW_ID%%}", data.rows[r].id).replace("{%%ROW_NAME%%}", data.rows[r].text)
          for (c = 0; c < data.cols.length; c++) {
            table += '<td class="statuscell" id="{%%ROW_ID%%}-{%%COLUMN_ID%%}" onclick="loadmodal(id)"></td>'.replace("{%%ROW_ID%%}", data.rows[r].id).replace("{%%COLUMN_ID%%}", data.cols[c].id)
          }
          table += "</tr>"
        }
        tableElement = document.getElementById('table');
        tableElement.innerHTML = table;
        structure = data
      }
    }

    // Update cells
    for (r = 0; r < data.rows.length; r++) {
      for (c = 0; c < data.cols.length; c++) {
        cellid = data.rows[r].id + "-" + data.cols[c].id;
        loadjson("data/"+cellid+".json", update_cell)
      }
    }
  }
}

function update_structure() {
  loadjson("data/structure.json", generate)
}

function start() {
  update_structure()
  setInterval(function () {
      update_structure()
    }, 10000);
}
