var groups = new vis.DataSet();
groups.add({
	id: 0,
	content: 'Fire temperature (oC)',
	className: 'fire',
	options: {
		drawPoints: {
			style: 'square',
			size: 8
		}
	}
});

groups.add({
	id: 1,
	content: 'Air temperature (oC)',
	className: 'air',
	options: {
		drawPoints: {
			style: 'circle',
			size: 10
		}
	}
});

groups.add({
	id: 2,
	content: 'Bean temperature (oC)',
	className: 'bean',
	options: {
		drawPoints: {
			style: 'circle',
			size: 15
		}
	}
});

var container = document.getElementById('visualization');
var dataset = new vis.DataSet();
var options = {
	dataAxis: {
		showMinorLabels: false,
	},
	legend: {left:{position:"bottom-left"}},
};
var graph2d = new vis.Graph2d(container, [], groups, options);
var textLog = $("#log");

function updateData() {
	$.ajax({
		url: "/message",
		success: function(data) {
			if (!data) {
				return;
			}
			for (index = 0; index < data.length; index++) {
				var row = data[index];
				if (row.data.message_type == "text") {
					textLog.html(textLog.html() + "<br>" + row.data.message);
					textLog.scrollTop(textLog.prop("scrollHeight"));
				}
				else if (row.data.message_type == "data") {
					graph2d.itemsData.update({
						x: row.data.timestamp,
						y: row.data.temp_fire,
						group: 0
					});
					graph2d.itemsData.update({
						x: row.data.timestamp,
						y: row.data.temp_air,
						group: 1
					});
					graph2d.itemsData.update({
						x: row.data.timestamp,
						y: row.data.temp_bean,
						group: 2
					});
				}
			}
		}
	});
	setTimeout(updateData, 1000);
}
updateData();
