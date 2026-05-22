# Pre-Deploy Audit Report — Spotify Playlist Manager

**Data:** 2026-05-22
**Commit:** `72a74d0`
**Ambiente target:** Produzione (Docker, reverse proxy)

---

## [CRITICO] Bug che bloccheranno il deployment o manderanno in crash l'app

### C1 — Assenza di validazione variabili d'ambiente all'avvio

- **File:** `backend/app/config.py`
- **Descrizione:** Le variabili `SPM_SLSKD_API_KEY`, `SPM_PROWLARR_API_KEY`, `SPM_QBITTORRENT_PASSWORD` e `SPM_MUSIC_PATH` non vengono validate al caricamento. Se vuote o assenti, l'applicazione parte comunque e il fallimento avviene solo a runtime quando i servizi esterni restituiscono errori 401/403/404. Un deployment con `.env` incompleto porterà a crash ritardati e difficili da diagnosticare.
- **Rischio:** Alto — deployment apparentemente riuscito, ma app inutilizzabile.
- **Fix:** Aggiungere Pydantic `BaseSettings` con validatori `Field(..., min_length=1)` per ogni variabile obbligatoria. Fallire all'avvio (exit code 1) se mancano variabili critiche.

### C2 — Paginazione Spotify senza guardia di massimo iterazioni

- **File:** `backend/app/services/spotify.py` (righe 67-114)
- **Descrizione:** Il loop `while True` per scorrere le pagine dei risultati API Spotify non ha un limite massimo di iterazioni. Se l'API restituisce valori `total` inconsistenti (ad esempio per errori di offset), il ciclo può proseguire indefinitamente causando un runaway.
- **Rischio:** Alto — consumo illimitato di risorse, app congelata.
- **Fix:** Aggiungere `max_pages = 100` (o calcolato da `total // limit + 1`) e un contatore; interrompere con `break` e log di warning se superato.

### C3 — `is_playable` default `True` maschera tracce bloccate geograficamente

- **File:** `backend/app/services/spotify.py` (riga 108)
- **Descrizione:** `track_obj.get("is_playable", True)` assume che una traccia sia disponibile se il campo manca. In realtà, Spotify omette `is_playable: false` solo per tracce bloccate in alcune regioni, ma il default `True` fa sì che il downloader tenti di scaricare brani inaccessibili, fallendo dopo aver sprecato risorse.
- **Rischio:** Medio-alto — falsi positivi nella sincronizzazione playlist, utente vede brani "disponibili" ma mai scaricati.
- **Fix:** Cambiare in `track_obj.get("is_playable", False)` e loggare un warning per ogni traccia esclusa.

### C4 — Chiamate HTTP a servizi esterni senza timeout

- **File:** `backend/app/services/slskd.py`, `backend/app/services/prowlarr.py`, `backend/app/services/qbittorrent.py`
- **Descrizione:** Tutte le richieste HTTP a slskd, Prowlarr e qBittorrent usano `httpx.AsyncClient` senza parametro `timeout`. Se un servizio è irraggiungibile, la connessione rimane in sospeso potenzialmente per minuti, bloccando i worker del downloader.
- **Rischio:** Alto — download bloccati, scheduler accumula task pendenti fino al crash per memoria.
- **Fix:** Impostare `timeout=httpx.Timeout(30.0, connect=10.0)` su tutti i client HTTP. Aggiungere retry con backoff esponenziale (max 3 tentativi).

### C5 — Lifespan di FastAPI senza gestione errori

- **File:** `backend/app/main.py` (lifespan context manager)
- **Descrizione:** `init_db()`, `setup_scheduler()` e `stop_scheduler()` sono chiamati direttamente senza try/except. Se uno di questi fallisce (ad esempio database corrotto, scheduler già avviato), l'eccezione si propaga fuori dal context manager, e FastAPI può silenziosamente sopprimerla, lasciando l'app in uno stato half-initialized senza log chiari.
- **Rischio:** Alto — malfunzionamento silenzioso, difficile da diagnosticare senza accesso diretto ai log del container.
- **Fix:** Avvolgere ogni step in try/except con `logger.error()` esplicito e chiamare `sys.exit(1)` in caso di fallimento critico.

### C6 — Race condition nei download concorrenti

- **File:** `backend/app/services/downloader.py`
- **Descrizione:** Quando più task di download operano concorrentemente, lo stesso brano può essere processato da due worker contemporaneamente. La scrittura su DB non è protetta da lock atomico a livello di applicazione.
- **Rischio:** Medio-alto — duplicati, corruzione dello stato del download queue, download inutili.
- **Fix:** Usare un `asyncio.Lock()` per la sezione critica di allocazione/scrittura download. Opzionalmente aggiungere un indice UNIQUE su `(track_id, playlist_id)` nel DB.

### C7 — `--forwarded-allow-ips=*` in Dockerfile

- **File:** `Dockerfile` (riga 40)
- **Descrizione:** `--forwarded-allow-ips=*` permette a qualsiasi client di falsificare gli header `X-Forwarded-For`, `X-Forwarded-Proto`, ecc. In produzione, questo abilita IP spoofing e bypassa i controlli di sicurezza basati sul client IP.
- **Rischio:** Alto — vulnerabilità di sicurezza se l'app è esposta (anche solo dietro reverse proxy).
- **Fix:** Specificare l'IP del reverse proxy (es. `--forwarded-allow-ips=172.17.0.1` per Docker, o l'IP del load balancer). Usare variabile d'ambiente.

---

## [WARNING] Problemi di performance, vulnerabilità minori o cattive pratiche

### W1 — Bare `except Exception` senza `logger.exception()`

- **File:** `backend/app/services/spotify.py` (righe 61, 116)
- **Descrizione:** Il catch cattura `Exception` in modo generico e logga solo un messaggio statico senza stack trace. Questo perde `KeyboardInterrupt` e `asyncio.CancelledError`, e rende il debug impossibile.
- **Rischio:** Medio — debugging difficoltoso, crash non rilevabili.
- **Fix:** Cambiare in `except (httpx.HTTPError, json.JSONDecodeError) as e:` e usare `logger.exception("message")`.

### W2 — Parsing fragile della pagina embed Spotify

- **File:** `backend/app/services/spotify.py` (riga 50)
- **Descrizione:** `text.split("window.__INITIAL_STATE__ = ")[1].split(";\n")[0]` è un parsing estremamente fragile. Se Spotify cambia il formato della pagina embed (aggiungendo spazi, cambiando la variabile, minificando il JS), il parsing produce un `IndexError` che viene catturato dall'outer `except Exception` con un messaggio poco informativo.
- **Rischio:** Medio — rottura imprevedibile in seguito ad aggiornamenti Spotify.
- **Fix:** Usare regex con fallback multipli, o meglio un parser HTML/JSON robusto. Eseguire test di integrazione periodici su pagine reali.

### W3 — Ricerca ricorsiva senza limite di profondità

- **File:** `backend/app/services/searcher.py`
- **Descrizione:** La scansione delle directory per file musicali non ha un parametro `maxdepth`. Se per errore viene scansionata una directory con annidamento profondo (es. `/music` contiene snapshot di filesystem), l'applicazione può consumare molta memoria e CPU.
- **Rischio:** Basso in condizioni normali, alto in scenari di errore.
- **Fix:** Impostare `maxdepth=5` o renderlo configurabile via `SPM_SCAN_MAX_DEPTH`.

### W4 — Login rinnovato ad ogni operazione qBittorrent

- **File:** `backend/app/services/qbittorrent.py`
- **Descrizione:** La connessione a qBittorrent effettua il login prima di ogni singola operazione. Questo spreca risorse di rete e CPU sia sul client che sul server qBittorrent.
- **Rischio:** Basso — overhead, non crash.
- **Fix:** Mantenere una sessione `httpx.AsyncClient` persistente con cookie di autenticazione. Rinnovare il login solo in caso di 403.

### W5 — SQLite senza WAL mode

- **File:** `backend/app/database.py`
- **Descrizione:** Il database SQLite non è configurato con `PRAGMA journal_mode=WAL`. In scenari con scritture concorrenti (download queue, aggiornamenti playlist), le performance degradano significativamente e si possono verificare `database is locked` error.
- **Rischio:** Medio — errori sporadici di concorrenza in produzione.
- **Fix:** Eseguire `PRAGMA journal_mode=WAL;` e `PRAGMA busy_timeout=5000;` all'apertura della connessione.

### W6 — Nessun lock distribuito per scheduler

- **File:** `backend/app/scheduler.py`
- **Descrizione:** Lo scheduler non implementa alcun meccanismo di lock distribuito. Se due istanze del container vengono avviate contemporaneamente (es. durante un rolling update in Docker Swarm o Kubernetes), entrambe eseguiranno le stesse operazioni pianificate (sincronizzazione playlist, scan libreria).
- **Rischio:** Medio — operazioni duplicate, race condition sui job.
- **Fix:** Usare un advisory lock SQLite (`SELECT GET_LOCK()`) o un file lock sul volume condiviso. Documentare che il servizio è single-instance.

### W7 — Frontend: nessun errore globale gestito

- **File:** `frontend/src/api/client.ts`
- **Descrizione:** Il client HTTP Axios/fetch non ha un interceptor globale per errori di rete, 5xx, o 4xx. Gli errori vengono propagati silenziosamente agli hook, che non li espongono all'UI. L'utente non sa mai se una richiesta è fallita.
- **Rischio:** Medio — UX degradata, diagnosi utente impossibile.
- **Fix:** Aggiungere un interceptor globale che mostra un toast di errore. Esporre `error` state in tutti gli hook.

### W8 — Frontend: hook non espongono `error` state

- **File:** `frontend/src/hooks/usePlaylists.ts`, `useDownloads.ts`, `useSettings.ts`
- **Descrizione:** I tipi di ritorno degli hook includono solo `data` e `loading`. Non espongono `error: string | null`. I componenti non possono distinguere tra "caricamento in corso" e "errore avvenuto".
- **Rischio:** Medio — UX degradata: schermate bianche/loader infiniti senza feedback.
- **Fix:** Aggiungere `error` al return type di ogni hook. Aggiungere handler per error state in ogni pagina.

### W9 — M3U8 generato senza verifica esistenza file

- **File:** `backend/app/services/playlist_builder.py`
- **Descrizione:** Il builder di playlist M3U8 aggiunge percorsi dei file senza verificare che i file esistano effettivamente sul filesystem. Se un file è stato spostato o cancellato dopo la generazione della playlist, l'M3U8 punta a path inesistenti.
- **Rischio:** Basso-medio — riproduttori musicali (Navidrome, VLC) mostrano tracce non riproducibili.
- **Fix:** Aggiungere una verifica `os.path.exists()` prima di includere ogni traccia; rimuovere quelle mancanti e loggare un warning.

### W10 — HEALTHCHECK perde la connettività

- **File:** `Dockerfile` (riga 38)
- **Descrizione:** Il comando `HEALTHCHECK` esegue `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"` ma l'endpoint `/api/health` **non esiste** nei router (non ho trovato una route `/api/health` in nessun file router). Il healthcheck fallirà sempre, causando riavvii continui del container da parte di Docker.
- **Rischio:** Alto in container orchestration — container killato e riavviato in loop.
- **Fix:** Creare un endpoint `/api/health` che restituisca `{"status": "ok"}` o alternativamente cambiare HEALTHCHECK in `curl -f http://localhost:8000/docs || exit 1`.

### W11 — build.sh pusha senza test

- **File:** `build.sh` (riga 21)
- **Descrizione:** Lo script di build esegue `docker push` incondizionatamente subito dopo la build, senza eseguire test (unit test, integration test) o sanity check.
- **Rischio:** Medio — immagini rotte pubblicate su Docker Hub.
- **Fix:** Aggiungere una fase di test tra build e push. Aggiungere flag `--dry-run` per push opzionale.

### W12 — Nessuna protezione contro symlink circolari nello scanner

- **File:** `backend/app/services/scanner.py`
- **Descrizione:** La scansione ricorsiva delle directory non controlla i symlink. Se esiste un symlink circolare (es. `music -> .`), lo scanner entra in un loop infinito consumando stack/CPU.
- **Rischio:** Basso in condizioni normali, alto con directory malformate.
- **Fix:** Tenere traccia dei path reali (`os.path.realpath()`) già visitati in un set; saltare gli inode già processati.

---

## [OTTIMIZZAZIONE] Consigli di refactoring e migliorie per produzione

### O1 — Aggiungere endpoint `/api/health`

- **File:** `backend/app/routers/` (nuovo file)
- **Descrizione:** Non esiste un endpoint healthcheck. È necessario per Docker HEALTHCHECK, Kubernetes liveness/readiness probe, e monitoraggio via Prometheus. L'attuale HEALTHCHECK in Dockerfile punta a `/api/health` che restituisce 404.
- **Azione:** Creare `backend/app/routers/health.py` con route `GET /api/health` che restituisca `{"status": "ok", "version": "..."}` e opzionalmente verifichi connettività a slskd/Prowlarr/qBittorrent (liveness) e stato DB (readiness).

### O2 — Validazione centralizzata con Pydantic Settings

- **File:** `backend/app/config.py`
- **Descrizione:** Sostituire il caricamento manuale delle variabili d'ambiente con `pydantic-settings` (`BaseSettings`). Questo dà validazione automatica, casting, valori di default documentati, e supporto per file `.env`.
- **Azione:** Installare `pydantic-settings` (già incluso in pydantic v2 via `pydantic_settings`). Creare classe `Settings(BaseSettings)` con ogni variabile tipata e validata.

### O3 — Timeout e retry pattern centralizzato per tutti i client HTTP

- **File:** Nuovo `backend/app/utils/http_client.py`
- **Descrizione:** I tre servizi HTTP (slskd, prowlarr, qbittorrent) condividono lo stesso pattern di connessione. Estrarre un client HTTP factory con timeout, retry, e logging preconfigurati.
- **Azione:** Creare una funzione `get_http_client(base_url, api_key=None, timeout=30)` che restituisca un `httpx.AsyncClient` configurato, da riutilizzare in tutti i servizi.

### O4 — Lock atomico per download queue

- **File:** `backend/app/services/downloader.py`
- **Descrizione:** Prevenire download duplicati con un lock a livello applicazione. Aggiungere `asyncio.Lock()` o usare SQLite `SELECT ... FOR UPDATE` tramite `aiosqlite` con `BEGIN IMMEDIATE`.
- **Azione:** Aggiungere un `DownloadLock` context manager che garantisca che ogni coppia `(track_id, playlist_id)` venga processata una sola volta.

### O5 — Pattern `loading | error | empty` su tutti i componenti React

- **File:** `frontend/src/pages/*.tsx`
- **Descrizione:** Ogni pagina React dovrebbe gestire esplicitamente quattro stati: caricamento, errore, vuoto, dati. Attualmente molte pagine gestiscono solo caricamento e dati.
- **Azione:** Per ogni pagina, aggiungere:
  ```tsx
  if (error) return <ErrorAlert message={error} onRetry={refetch} />;
  if (loading) return <Loader />;
  if (!data || data.length === 0) return <EmptyState />;
  return <DataView data={data} />;
  ```

### O6 — Cache delle sessioni per servizi esterni

- **File:** `backend/app/services/qbittorrent.py`, `slskd.py`, `prowlarr.py`
- **Descrizione:** Ogni richiesta a qBittorrent fa un nuovo login. Ogni richiesta a slskd invia l'API key senza caching. Introdurre un meccanismo di caching per ridurre il carico di rete.
- **Azione:** Mantenere un dict `{service: {"client": AsyncClient, "expires": timestamp}}` con refresh automatico del client in caso di errore 401/403.

### O7 — Documentare e forzare la configurazione in docker-compose.yml

- **File:** `docker-compose.yml`, `.env.example`
- **Descrizione:** Il `docker-compose.yml` contiene valori di default insicuri. Il `.env.example` è corretto ma non comunica chiaramente che alcune variabili sono obbligatorie.
- **Azione:** Modificare `docker-compose.yml`: rimuovere tutti i valori hardcoded. Mettere commenti `# REQUIRED` su ogni variabile. Modificare `.env.example` con lo stesso marker.

### O8 — Logging strutturato in JSON

- **File:** `backend/app/main.py`, `backend/app/config.py`
- **Descrizione:** In ambiente containerizzato, i log in formato testo semplice sono difficili da parsare con strumenti come Loki, ELK o Datadog.
- **Azione:** Aggiungere `python-json-logger` come dipendenza opzionale. Configurare un `JSONFormatter` quando `SPM_LOG_FORMAT=json`. Loggare come JSON per production, testo per sviluppo.

### O9 — Protezione CORS in produzione

- **File:** `backend/app/main.py`
- **Descrizione:** La configurazione CORS attuale permette `allow_origins=["*"]` (da verificare nel codice). In produzione con frontend separato, questo va ristretto all'origine specifica del frontend.
- **Azione:** Usare `SPM_CORS_ORIGINS` come variabile d'ambiente per configurare origini consentite. Default a `*` in sviluppo, richiedere valore esplicito in produzione.

### O10 — Aggiungere test automatizzati pre-deploy

- **File:** Nuova directory `backend/tests/`
- **Descrizione:** Non ci sono test nel codebase (nessun file `test_*.py` trovato). Il deployment in produzione senza test è estremamente rischioso.
- **Azione:** Implementare almeno:
  - Test unitari per `config.py` (validazione env)
  - Test di integrazione per `spotify.py` (paginazione, parsing)
  - Test per `downloader.py` (race condition, lock)
  - Test API per ogni router (usando `TestClient` di FastAPI)

---

## Riepilogo

| Categoria | Conteggio | Impatto |
|-----------|-----------|---------|
| [CRITICO] | 7 | Bloccante per il deployment |
| [WARNING] | 12 | Rischi medio-bassi, da pianificare |
| [OTTIMIZZAZIONE] | 10 | Migliorie consigliate |

**Raccomandazione:** Risolvere tutti i 7 CRITICI prima del deployment. I WARNING vanno risolti entro il primo sprint post-deploy. Le OTTIMIZZAZIONI possono essere pianificate nel backlog tecnico.
