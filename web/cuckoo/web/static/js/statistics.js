(async function() {

  const loader = document.querySelector('.loader.loader-cuckoo');
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

  function renderChart(stats) {

    let { type, data } = stats;
    let label = stats.name;
    let desc = stats.description;

    const container = document.createElement('div');
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    view.appendChild(container);
    canvas.style.maxHeight = '500px';

    // global chart setup configuration
    const chartSetup = {
      type,
      data: {
        datasets: []
      }
    };

    // create a line chart for chart.type = line
    if(type === 'line') {
      chartSetup.data.datasets.push({
        label,
        data: data.map(p => {
          return {
            x: p.label,
            y: p.value
          }
        })
      });
      const chart = new Chart(canvas.getContext('2d'), chartSetup);
    }
    // create a bar chart for chart.type = bar
    if(type == 'bar') {
      chartSetup.data.labels = data.map(p => p.label);
      chartSetup.data.datasets.push({ label, data: data.map(p => p.value) })
      const chart = new Chart(canvas.getContext('2d'), chartSetup);
    }

  }

  setTimeout(() => {
    stopLoader(() => {
      if(statistics.length) statistics.forEach(renderChart);
    });
  }, 1000);

}());
