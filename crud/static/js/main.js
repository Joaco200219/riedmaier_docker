
const btnDelete= document.querySelectorAll('.btn-borrar');
if(btnDelete) {
  const btnArray = Array.from(btnDelete);
  btnArray.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      if(!confirm('¿Está seguro de querer borrar?')){
        e.preventDefault();
      }
    });
  })
}


document.addEventListener('DOMContentLoaded', () => {
    const themeStyle = document.getElementById('theme-stylesheet');
    const dropdownItems = document.querySelectorAll('.dropdown-item[data-theme]');

    // URLs de los archivos CSS de Bootswatch
    const themes = {
        light: 'https://bootswatch.com/5/cosmo/bootstrap.min.css',
        dark: 'https://bootswatch.com/5/darkly/bootstrap.min.css'
    };

    // 1. Cargar la preferencia guardada al iniciar la página (por defecto es 'light')
    const savedTheme = localStorage.getItem('user-theme') || 'light';
    themeStyle.setAttribute('href', themes[savedTheme]);

    // 2. Escuchar los clics en las opciones del menú desplegable
    dropdownItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault(); // Evita que la página salte al hacer clic
            const selectedTheme = item.getAttribute('data-theme');
            
            // Cambiar el archivo CSS dinámicamente
            themeStyle.setAttribute('href', themes[selectedTheme]);
            
            // Guardar la elección en el almacenamiento local del navegador
            localStorage.setItem('user-theme', selectedTheme);
        });
    });
});