(async function() {

  const container   = document.querySelector('#statistics');
  const loader      = document.querySelector('.loader.loader-cuckoo');
  const colorScheme = ['#003f5c','#2f4b7c','#665191','#a05195','#d45087','#f95d6a','#ffa600'];
  let lto;

  window.startLoader = function startLoader(next) {
    if(lto) clearTimeout(lto);
    loader.classList.remove('loader-hidden');
    lto = setTimeout(() => {
      loader.classList.remove('loader-out');
      if(next instanceof Function) next();
    }, 10);
  }

  window.stopLoader = function stopLoader(next) {
    loader.classList.add('loader-out');
    if(lto) clearTimeout(lto);
    lto = setTimeout(() => {
      loader.classList.add('loader-hidden');
      if(next instanceof Function) next();
    }, 500);
  }

  async function getStatistics() {
    return fetch('/static/js/mock/statistics.mock.json', {
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
          <div class="has-padding-y">
            <canvas></canvas>
          </div>
        </div>
      </div>
    `);
  }

  /*
   * renders a chart based on the input chart type, and utilizes chartView
   * to construct the required DOM markup before appending it to the DOM for
   * display.
   */
  function renderChart(stats) {

    let { type, data, name, description  } = stats;

    let view      = chartView({ name, description });
    let canvas    = view.querySelector('canvas');
    let ctx       = canvas.getContext('2d');

    // global chart setup configuration
    const chartSetup = {
      type,
      data: {
        datasets: []
      },
      options: {
        color: colorScheme,
        // responsive: false,
        maintainAspectRatio: false,
        animation: {
          duration: 0
        },
        datasets: {
          bar: { backgroundColor: colorScheme },
          line: { fill: 'origin' }
        },
        plugins: {
          legend: {
            display: false
          }
        }
      }
    };
    // create a line chart for chart.type = line
    if(type === 'line') {
      chartSetup.data.datasets.push({
        label: name,
        data: data.map(p => {
          return {
            x: p.label,
            y: p.value
          }
        })
      });
      const chart = new Chart(ctx, chartSetup);
    }
    // create a bar chart for chart.type = bar
    if(type == 'bar') {
      chartSetup.data.labels = data.map(p => p.label);
      chartSetup.data.datasets.push({
        label: name,
        data: data.map(p => p.value)
      });
      const chart = new Chart(ctx, chartSetup);
    }

    container.appendChild(view);

  }

  setTimeout(() => {
    stopLoader(() => {
      if(statistics.length) statistics.forEach(renderChart);
    });
  }, 1000);

}());
