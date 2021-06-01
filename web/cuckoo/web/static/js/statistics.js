(async function() {

  const apiURL      = window.location.origin + "/api/statistics/charts";
  const container   = document.querySelector('#statistics');
  const loader      = document.querySelector('.loader.loader-cuckoo');
  const colorScheme = ['#003f5c','#f95d6a','#ffa600','#2f4b7c','#a05195','#d45087','#665191'];
  const defaults    = { color: colorScheme, maintainAspectRatio: false, animation: false };
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

  // starts the async loader symbol
  window.startLoader = function startLoader(next) {
    if(lto) clearTimeout(lto);
    loader.classList.remove('loader-hidden');
    lto = setTimeout(() => {
      loader.classList.remove('loader-out');
      if(next instanceof Function) next();
    }, 10);
  }

  // stops the async loader symbol
  window.stopLoader = function stopLoader(next) {
    loader.classList.add('loader-out');
    if(lto) clearTimeout(lto);
    lto = setTimeout(() => {
      loader.classList.add('loader-hidden');
      if(next instanceof Function) next();
    }, 500);
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
  const statistics = await getStatistics();
  const view = document.querySelector('#statistics');

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
              ${ name ? `<h4 class="no-margin-y">${name}</h4>` : '' }
              ${ description ? `<p class="no-margin-y">${description}</p>` : '' }
            </div>
            <!-- <div class="columns"><span class="tag has-background-white">{chart controls}</span></div> -->
          </div>
          <div class="has-padding-y box-content">
            <canvas></canvas>
          </div>
        </div>
      </div>
    `);
  }

  /*
   * returns error element for view
   */
  function viewError(data="") {
    return parseDOM(`<p class="is-error">${data}</p>`);
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
      set.pointBackgroundColor = rgbfy(colorScheme[i]);
      set.backgroundColor = rgbfy(colorScheme[i], .5);
      set.borderColor = rgbfy(colorScheme[i], 1);
      return set;
    });

    return new Chart(canvas.getContext('2d'), {
      data,
      type: 'line',
      options: {
        ...defaults,
        datasets: {
          line: {
            fill: 'origin',
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
            stacked: isMultiple
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: label => false,
              yAlign: 'top',
              xAlign: 'center'
            }
          },
          legend: {
            display: isMultiple
          }
        },
        interaction: {
          intersect: false
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

    container.appendChild(view);

  }

  setTimeout(() => {
    stopLoader(() => {
      if(statistics.length) statistics.forEach(renderChart);
    });
  }, 1000);

}());
