(function() {

  /**
   * Implementation of web component that renders a ticking countdown
   * @attribute start - ISO date when started
   * @attribute end - time to elapse in seconds
   *
   * The component will calculate when the countdown stops by adding the number
   * of seconds to the start date. Then it displays like hh:mm:ss, ticking down.
   *
   * Example:
   *
   * <countdown-timer start="2021-10-25 12:31:15.759938" end="300"></countdown-timer>
   *
   * - above tag with setup will countdown to 300 seconds after that initial start date
   */

  // replace for luxon
  if(!window.luxon) {
    console.error('requires luxon.js');
    return false;
  };

  class CountdownTimer extends HTMLElement {

    interval = null;
    from = null;
    to = null;
    to_format = "seconds";

    constructor() {
      super();
      this.attachShadow({ mode: 'open' });

      this.countdownNode = document.createElement('p');
      this.countdownNode.style.margin = 0 + 'px';
      this.shadowRoot.append(this.countdownNode);
    }

    tick() {
      const dur = new luxon.Duration(this.to.diff(luxon.DateTime.now()));
      if(dur.milliseconds < 0) {
        this.interval = clearInterval(this.interval);
        this.countdownNode.textContent = '00:00:00';
      } else {
        this.countdownNode.textContent = dur.toFormat('hh:mm:ss');
      }
    }

    initDuration() {

      const dateString = this.getAttribute('start').split('.')[0].replace(" ","T") + 'Z';
      const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      this.from = luxon.DateTime.fromISO(dateString, { zone: timeZone });
      this.to = this.from.plus({ seconds: parseInt(this.getAttribute('end')) });

      const diff = luxon.Interval.fromDateTimes(this.from, this.to);

      if(this.interval)
        this.interval = clearInterval(this.interval);
      this.interval = setInterval(() => this.tick(), 1000);
      this.tick();
    }

    attributeChangedCallback(name, oldValue, newValue) {
      switch(name) {
        case "start":
        case "end":
          this.initDuration();
        break;
      }
    }

    static get observedAttributes() {
      return ['start', 'end'];
    }

  }

  customElements.define('countdown-timer', CountdownTimer);

}());
