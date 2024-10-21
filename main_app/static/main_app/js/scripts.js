$(document).ready(function() {
    // Animation pour les boutons
    $(".btn").hover(function() {
        $(this).addClass('shadow-lg').css('transition', '0.3s');
    }, function() {
        $(this).removeClass('shadow-lg');
    });

    // Smooth scroll pour les liens
    $('a.nav-link').on('click', function(event) {
        if (this.hash !== "") {
            event.preventDefault();
            $('html, body').animate({
                scrollTop: $(this.hash).offset().top
            }, 800);
        }
    });
});
