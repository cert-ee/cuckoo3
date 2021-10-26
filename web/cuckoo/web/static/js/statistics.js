(async function() {

  if(!window.statistics_enabled) {
    console.warn('Statistics feature is disabled. Enable feature in configuration.');
    return;
  }

  // use page-specific loader element
  lib.loaderElement = document.querySelector('#statistics-loader');

  const apiURL      = window.location.origin + "/api/statistics/charts";
  const container   = document.querySelector('#statistics');
  const colorScheme = [
    '#FF0000','#00FF00','#0000FF','#FFFF00','#00FFFF','#FF00FF',
    '#0048BA','#B0BF1A','#7CB9E8','#C0E8D5','#72A0C1','#FFBF00','#3DDC84','#FF91AF',
    '#FE6F5E','#79443B','#003f5c','#f95d6a','#ffa600','#2f4b7c','#a05195','#d45087',
    '#665191','#D891EF','#A67B5B','#E03C31','#0047AB','#DC143C','#006400','#555555',
    '#6F00FF'
  ];

  const defaults    = {
    maintainAspectRatio: false,
    animation: false
  };
  let lto; // timeout cache

  // utility: convert hex value to rgb
  // example: rgbfy(colorScheme[1]);
  function rgbfy(hex, alpha=1) {
    let result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if(result) {
      let values = result.map(res => parseInt(res, 16) || 0).splice(1, 3);
      if(typeof alpha == "number")
        values.push(alpha);
      return `rgba(${values.join(',')})`;
    }
  }

  /*
   * retrieves statistics data from the API in a Promise wrapper (HTTP Fetch)
   */
  async function getStatistics() {
    return fetch(apiURL, {
      headers: new Headers({ 'Content-Type': 'application/json' })
    }).then(res => res.json());
  }

  startLoader();
  const view = document.querySelector('#statistics');
  const statistics = await getStatistics();

  if(statistics.error) {
    const err = viewError(statistics.error);
    err.style.marginLeft = 'auto';
    err.style.marginRight = 'auto';
    view.parentNode.appendChild(err);
    stopLoader();
    return;
  }

  /*
   * renders a selection of dom elements to render a single chart in.
   * the output can be appended to the target location using appendChild
   */
  function chartView(data={}) {
    let { name, description } = data;
    return parseDOM(`
      <div style="overflow: auto">
        <div class="box has-background-white no-padding no-radius no-margin-y">
          <div class="box-title no-radius columns is-between is-vcenter is-gapless no-margin-top">
            <div class="column">
              ${ name ? `<h4 class="no-margin-y">${lib.SafeString(name)}</h4>` : '' }
              ${ description ? `<p class="no-margin-y">${lib.SafeString(description)}</p>` : '' }
            </div>
          </div>
          <div class="has-padding-y box-content">
            <canvas style="height: 16rem"></canvas>
          </div>
        </div>
      </div>
    `);
  }

  /*
   * returns error element for view
   */
  function viewError(data="") {
    return parseDOM(`
      <div class="banner is-red">
        <span class="banner-icon">
          <i class="fas fa-exclamation-triangle"></i>
        </span>
        <p>${lib.SafeString(data)}</p>
      </div>
    `);
  }

  /*
   * returns a bar chart instance trough the Chart api
   */
  function createBarChart(canvas, data) {
    let { datasets, labels } = data;

    datasets = datasets.map(p => {
      p.backgroundColor = colorScheme.map(c => rgbfy(c, .5));
      p.borderColor = colorScheme;
      return p;
    });

    return new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        datasets,
        labels
      },
      options: {
        ...defaults,
        elements: {
          bar: {
            borderWidth: 1.5
          }
        },
        plugins: {
          legend: {
            display: false
          }
        }
      },
    });
  }

  /*
   * returns a line chart instance trough the Chart api
   */
  function createLineChart(canvas, data) {

    // (!) if datasets > 0, make sure it behaves as a stacked line chart
    const { datasets, labels } = data;
    const isMultiple = (datasets.length > 1);

    data.datasets = datasets.map((set, i) => {
      set.pointBackgroundColor = rgbfy(colorScheme[i % colorScheme.length + 1]);
      set.backgroundColor = rgbfy(colorScheme[i % colorScheme.length + 1], .5);
      set.borderColor = rgbfy(colorScheme[i % colorScheme.length + 1], 1);
      return set;
    });

    return new Chart(canvas.getContext('2d'), {
      data,
      type: 'line',
      options: {
        ...defaults,
        datasets: {
          scaleFontColor: '#FFFFFF',
          line: {
            fill: false,
            // fill: 'origin',
            pointRadius: 2,
            pointHitRadius: 10,
            pointBorderWidth: 1,
            borderWidth: 1.5,
            borderCapStyle: 'round', // 'round', 'butt' or 'square'
            borderJoinStyle: 'round' // 'bevel', 'round' or 'miter'
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            // stacked: isMultiple
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              // label: label => false,
              yAlign: 'top',
              xAlign: 'center'
            }
          },
          legend: {
            display: isMultiple
          }
        },
        interaction: {
          // intersect: false
        }
      }
    });
  }

  /*
   * renders a chart based on the input chart type, and utilizes chartView
   * to construct the required DOM markup before appending it to the DOM for
   * display.
   */
  function renderChart(stats) {

    let { type, data, name, description  } = stats;

    let view = chartView({ name, description });
    container.appendChild(view);

    let chart;
    switch(type) {
      case 'line':
        chart = createLineChart(view.querySelector('canvas'), stats);
      break;
      case 'bar':
        chart = createBarChart(view.querySelector('canvas'), stats);
      break;
      default:
        view.querySelector('canvas').remove();
        view.querySelector('.box-content').appendChild(viewError(`'${type}' is not supported as cart type.`))
    }

    chart.resize();

  }

  stopLoader(() => {
    if(statistics.length) statistics.forEach(renderChart);
  });

}());
