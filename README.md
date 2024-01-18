# MyMovies

MyMovies este o aplicație web tip IMDb dezvoltată în Python cu ajutorul framework-ului Flask menită să ajute utilizatorii în organizrea și evaluarea filmelor vizionate. În cadrul acestui proiect au fost implementate 4 microservicii: *“users”*, *“movies”*, *“ratings_reviews”* și *“watchlists”*.

Microserviciul *“users”* conține tabelul **users** și gestionează operațiile de adăugare și listare a utilizatorilor aplicației. Informațiile unui user sunt nume de utilizator, email și data nașterii (primele 2 trebuind să fie unice la nivelul bazei de date).

Serviciul *“movies”* conține tabelele **genres** și **movies**, fiecare film aparținând unui gen cinematografic dominant. Prin intermediul lui putem adăuga și afișa toate genurile, putem adăuga și lista filmele în funcție de gen și putem șterge un anumit film.

Utilizatorii pot adăuga filme în lista lor de vizionări prin intermediul microserviciului *“watchlists”* ce conține tabelul **watchlist**. Ulterior, din pagina de useri, aceștia își pot vizualiza lista pentru a ține evidența filmelor vizionate sau pe care plănuiesc să le urmărească în viitor. 

În final, utilizatorii pot evalua și nota filmele văzute prin intermediul serviciului *“ratings_reviews”* ce conține tabelele **ratings** și **reviews**. Din pagina de informații ale unui film (ce conține detalii precum an de lansare, durată și nota medie) aceștia pot vedea comentariile celorlalți useri, pot adăuga o recenzie și pot acorda note de la 1 la 10 filmelor.

Aplicația conține baze de date **MySql** separate pentru fiecare microserviciu și a fost utilizat **Zipkin** pentru urmărirea request-urilor. Pentru înregistrarea metricilor precum numărul de request-uri și timpul de execuție este folosit **Prometheus**.

Pentru pornirea containerelor (cele 4 microservicii, imaginea de MySql, imaginea de Zipkin și imaginea de Prometheus) se folosește **docker-compose**, iar pentru scalare a fost utilizat **Docker Swarm**.
