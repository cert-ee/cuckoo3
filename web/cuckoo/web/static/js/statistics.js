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

  const statistics = await getStatistics();
  const display = document.querySelector('#statistics-display');

  if(!display)
    return;

  const chart =  new Chart(display.getContext("2d"), {
    type: "line",
    data: {
      datasets: [{
        label: 'Analyses/day',
        data: statistics.analyses.map(a => {
          return {
            x: a.ts,
            y: a.value
          }
        })
      }]
    }
  });

}());
