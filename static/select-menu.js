// Keep the real select for form values; draw a consistent, keyboard-friendly menu.
(() => {
  const menus = [];

  for (const select of document.querySelectorAll('select')) {
    const label = select.closest('label');
    const name = label
      ? [...label.childNodes].filter(node => node.nodeType === 3).map(node => node.textContent).join('').trim()
      : select.getAttribute('aria-label') || 'Choose an option';
    const wrapper = document.createElement('div');
    wrapper.className = 'select-menu';
    select.before(wrapper);
    wrapper.appendChild(select);
    select.classList.add('select-native');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.id = `${select.id}-trigger`;
    trigger.className = 'select-trigger';
    trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', `${select.id}-options`);
    if (label) label.htmlFor = trigger.id;

    const value = document.createElement('span');
    const chevron = document.createElement('span');
    chevron.className = 'select-chevron';
    chevron.setAttribute('aria-hidden', 'true');
    trigger.append(value, chevron);

    const list = document.createElement('div');
    list.id = `${select.id}-options`;
    list.className = 'select-options';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-label', name);
    list.hidden = true;
    wrapper.append(trigger, list);
    let activeIndex = select.selectedIndex;
    let typed = '';
    let typedAt = 0;

    const options = [...select.options].map((option, index) => {
      const item = document.createElement('div');
      item.id = `${select.id}-option-${index}`;
      item.className = 'select-option';
      item.setAttribute('role', 'option');
      item.textContent = option.textContent;
      item.addEventListener('mousedown', event => event.preventDefault());
      item.addEventListener('click', event => {
        event.preventDefault();
        choose(index);
      });
      list.appendChild(item);
      return item;
    });

    function sync() {
      value.textContent = select.selectedOptions[0]?.textContent || '';
      trigger.setAttribute('aria-label', `${name}: ${value.textContent}`);
      options.forEach((item, index) => {
        item.setAttribute('aria-selected', String(index === select.selectedIndex));
        item.classList.toggle('highlighted', index === activeIndex);
      });
    }

    function close() {
      list.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.removeAttribute('aria-activedescendant');
      wrapper.classList.remove('is-open');
    }

    function open() {
      menus.forEach(menu => menu.close());
      activeIndex = select.selectedIndex;
      list.hidden = false;
      wrapper.classList.add('is-open');
      trigger.setAttribute('aria-expanded', 'true');
      highlight();
    }

    function highlight() {
      sync();
      trigger.setAttribute('aria-activedescendant', options[activeIndex].id);
      options[activeIndex].scrollIntoView({block: 'nearest'});
    }

    function choose(index) {
      select.selectedIndex = index;
      activeIndex = index;
      sync();
      close();
      // Existing form handlers still receive the same value and events.
      select.dispatchEvent(new Event('input', {bubbles: true}));
      select.dispatchEvent(new Event('change', {bubbles: true}));
      trigger.focus();
    }

    trigger.addEventListener('click', () => list.hidden ? open() : close());
    trigger.addEventListener('keydown', event => {
      if (event.key === 'Escape' || event.key === 'Tab') {
        close();
        return;
      }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)) {
        event.preventDefault();
        if (list.hidden) {
          open();
          return;
        }
        if (event.key === 'Enter' || event.key === ' ') {
          choose(activeIndex);
          return;
        }
        if (event.key === 'Home') activeIndex = 0;
        else if (event.key === 'End') activeIndex = options.length - 1;
        else activeIndex = (activeIndex + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
        highlight();
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
        const now = Date.now();
        typed = now - typedAt > 700 ? event.key : typed + event.key;
        typedAt = now;
        const match = [...select.options].findIndex(option => option.textContent.toLowerCase().startsWith(typed.toLowerCase()));
        if (match >= 0) {
          if (list.hidden) open();
          activeIndex = match;
          highlight();
        }
      }
    });
    wrapper.addEventListener('focusout', event => {
      if (!wrapper.contains(event.relatedTarget)) close();
    });
    select.addEventListener('change', sync);
    select.form?.addEventListener('reset', () => setTimeout(() => {
      activeIndex = select.selectedIndex;
      close();
      sync();
    }, 0));
    document.addEventListener('pointerdown', event => {
      if (!wrapper.contains(event.target)) close();
    });
    menus.push({close});
    sync();
  }
})();
