//     Description    Flame Predict JavaScript 
//
//     Authors:       Manuel Pastor (manuel.pastor@upf.edu)
// 
//     Copyright 2018 Manuel Pastor
// 
//     This file is part of Flame
// 
//     Flame is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation version 3.
// 
//     Flame is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
// 
//     You should have received a copy of the GNU General Public License
//     along with Flame. If not, see <http://www.gnu.org/licenses/>.

// parse results obtained from the prediction
function parseResults (results) {
    $("#data-body").text(results);

    const headers = ['#','name','prediction','CI','RI']
    var tbl_body = '<thead><tr>'
    for (i in headers){
        tbl_body += '<th>'+headers[i]+'</th>'
    }
    tbl_body+='</tr></thead>'
    
    var myjson = JSON.parse(results);

    for (i in myjson['projection']){
        tbl_body += "<tr><td>"+(parseInt(i)+1)+
                    "</td><td>"+myjson['obj_nam'][i]+
                    "</td><td>"+myjson['projection'][i].toFixed(4)+
                    "</td><td>"+myjson['CI'][i]+
                    "</td><td>"+myjson['RI'][i]+
                    "</td></tr>";
    }

    $("#data-table").html(tbl_body);   
};

// POST a prediction request for the selected model, version and input file
function postPredict (temp_dir, ifile) {
    // collect all data for the post and insert into postData object

    var version = $("#version option:selected").text();
    if (version=='dev') {
        version = '0';
    };

    $.post('/predict', {"ifile"   : ifile,
                        "model"   : $("#myselect option:selected").text(),
                        "version" : version,
                        "temp_dir": temp_dir
                        })
    .done(function(results) {
        parseResults (results)
    });
};

// main
$(document).ready(function() {

    // initialize button status to disabled on reload
    $("#predict").prop('disabled', true);


    // show file value after file select 
    $("#ifile").on('change',function(){
        file = document.getElementById("ifile").files[0];
        $("#ifile-label").html( file.name ); 
        $("#predict").prop('disabled', false);
    })

    // TODO: send a GET dir for completing the list of models
    // in a second step, complete get to return also the versions and include these too


    $.get('/dir')
    .done(function(results) {
        var versions = JSON.parse(results);
        for (vi in versions) {
            console.log(versions[vi])
            imodel = versions[vi][0];
            console.log(imodel);
            vmodel = versions[vi][1];
            for (vj in vmodel) {
                console.log (vmodel[vj]);
            }
        }
        
    });

    // "predict" button
    $("#predict").click(function(e) {

        // make sure the browser can upload XMLHTTP requests
        if (!window.XMLHttpRequest) {
            $("#data-body").text("this browser does not support file upload");
            return;
        };

        // clear GUI
        $("#data-body").text('processing... please wait');
        $("#data-table").html('');
         
        // get the file 
        var ifile = document.getElementById("ifile").files[0];
        
        // generate a random dir name
        var temp_dir = randomDir();

        // call postPredict when file upload is completed
        if (upload(ifile, temp_dir, postPredict)==false) {
            $("#data-body").text("unable to upload file, prediction aborted...");
            return;
        };

        e.preventDefault(); // from predict click function
    });


});