/**
 * Interface chat (point 3) : login JWT (/auth/login), inscription (/auth/register),
 * messages /chat avec Bearer, persistance historique (localStorage) et session (sessionStorage).
 * Au montage : GET /auth/me si un token existe déjà (validation sans boucle sur le JWT).
 * Cartes cours : lignes bot commençant par « — » (aligné sur _fmt_ev côté API).
 */
import { useCallback, useEffect, useMemo, useState } from "react";

type BackendStatus = "checking" | "online" | "offline";
type AuthMode = "login" | "register";
type CourseCard = {
  matiere: string;
  type: string;
  horaire: string;
  salle: string;
  enseignant: string;
};
type ChatLine = {
  who: "user" | "bot";
  text: string;
  courses?: CourseCard[];
  /** Intent renvoyé par l’API (démo / debug pédagogique). */
  intent?: string;
  needsConfirmation?: boolean;
};
type AuthUser = {
  email: string;
  role: string;
  groupe: string | null;
};

// URL API : surcharger avec VITE_API_URL dans .env du frontend si besoin.
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const STORAGE_KEY = "tfckerensiki-chat-history-v1";
const TOKEN_KEY = "tfckerensiki-token-v1";
const AUTH_USER_KEY = "tfckerensiki-user-v1";
const WELCOME_MESSAGE =
  "Salut — Université de Kinshasa, Faculté Polytechnique. Tu es connecté en L3GIN : demande tes horaires en français.";

/** Extrait les créneaux structurés depuis le texte renvoyé par l’API (une ligne = un cours). */
function parseCoursesFromReply(reply: string): CourseCard[] {
  const rows = reply
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("— "));

  return rows
    .map((row) => {
      const m = row.match(/^—\s(.+?)\s\((.+?)\),\s(.+?),\ssalle\s(.+?),\s(.+)$/i);
      if (!m) return null;
      return {
        matiere: m[1],
        type: m[2],
        horaire: m[3],
        salle: m[4],
        enseignant: m[5],
      } satisfies CourseCard;
    })
    .filter((x): x is CourseCard => x !== null);
}

export function App() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");

  // --- Connexion ---
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);

  // --- Inscription ---
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regGroupe, setRegGroupe] = useState("");
  const [registerError, setRegisterError] = useState<string | null>(null);

  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [authUser, setAuthUser] = useState<AuthUser | null>(() => {
    try {
      const raw = sessionStorage.getItem(AUTH_USER_KEY);
      return raw ? (JSON.parse(raw) as AuthUser) : null;
    } catch {
      return null;
    }
  });
  const [input, setInput] = useState("");
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [lines, setLines] = useState<ChatLine[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [{ who: "bot", text: WELCOME_MESSAGE }];
      const parsed = JSON.parse(raw) as ChatLine[];
      return parsed.length > 0 ? parsed : [{ who: "bot", text: WELCOME_MESSAGE }];
    } catch {
      return [{ who: "bot", text: WELCOME_MESSAGE }];
    }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Sauvegarde automatique de l’historique de chat côté navigateur.
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
  }, [lines]);

  useEffect(() => {
    // Sonde /health toutes les 15 s pour l’indicateur « backend connecté ».
    let cancelled = false;
    const check = async () => {
      try {
        const r = await fetch(`${API_BASE}/health`);
        if (!cancelled) setBackendStatus(r.ok ? "online" : "offline");
      } catch {
        if (!cancelled) setBackendStatus("offline");
      }
    };
    void check();
    const timer = window.setInterval(() => void check(), 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  // Phrases rapides : variante agent (annulation) vs étudiant (consultation).
  const suggestions = useMemo(() => {
    if (authUser?.role === "AGENT" || authUser?.role === "RESPONSABLE") {
      return [
        "Quel est mon prochain cours ?",
        "Montre-moi ma semaine",
        "Annule le cours de Travaux de Programmation groupe L3GIN",
        "Déplace le cours de Internet Engineering demain",
        "Mets le cours de Programmation Orientée Objet en salle H",
      ];
    }
    return [
      "Quel est mon prochain cours ?",
      "Mes cours aujourd'hui",
      "Montre-moi ma semaine",
    ];
  }, [authUser?.role]);

  const applyAuthResult = useCallback(
    (data: { access_token: string; email: string; role: string; groupe: string | null }) => {
      setToken(data.access_token);
      sessionStorage.setItem(TOKEN_KEY, data.access_token);
      const user = { email: data.email, role: data.role, groupe: data.groupe };
      setAuthUser(user);
      sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
      setLines([{ who: "bot", text: WELCOME_MESSAGE }]);
      localStorage.setItem(STORAGE_KEY, JSON.stringify([{ who: "bot", text: WELCOME_MESSAGE }]));
    },
    [],
  );

  const login = useCallback(async () => {
    // POST /auth/login → stocke JWT + profil minimal pour l’UI.
    setAuthError(null);
    try {
      const r = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || "Login refusé");
      }
      const data = (await r.json()) as {
        access_token: string;
        email: string;
        role: string;
        groupe: string | null;
      };
      applyAuthResult(data);
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e);
      setAuthError(err);
    }
  }, [email, password, applyAuthResult]);

  const register = useCallback(async () => {
    // POST /auth/register → crée le compte étudiant, puis connecte automatiquement.
    setRegisterError(null);
    try {
      const r = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: regEmail, password: regPassword, groupe: regGroupe }),
      });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || "Inscription refusée");
      }
      const data = (await r.json()) as {
        access_token: string;
        email: string;
        role: string;
        groupe: string | null;
      };
      applyAuthResult(data);
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e);
      setRegisterError(err);
    }
  }, [regEmail, regPassword, regGroupe, applyAuthResult]);

  const logout = useCallback(() => {
    setToken(null);
    setAuthUser(null);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(AUTH_USER_KEY);
  }, []);

  // Au premier rendu uniquement : JWT déjà en session → GET /auth/me pour valider et rafraîchir le profil.
  // Pas de `token` en dépendance : chaque /auth/me renvoie un nouveau JWT → risque de boucle infinie.
  useEffect(() => {
    const stored = sessionStorage.getItem(TOKEN_KEY);
    if (!stored) return;
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${stored}` },
        });
        if (cancelled) return;
        if (r.status === 401) {
          logout();
          return;
        }
        if (!r.ok) return;
        const data = (await r.json()) as {
          access_token: string;
          email: string;
          role: string;
          groupe: string | null;
        };
        if (cancelled) return;
        setToken(data.access_token);
        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        const user = { email: data.email, role: data.role, groupe: data.groupe };
        setAuthUser(user);
        sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
      } catch {
        /* réseau indisponible : on conserve le token, /health indiquera l’état */
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- exécution unique au montage
  }, [logout]);

  const send = useCallback(
    async (rawInput?: string) => {
    // POST /chat : corps { message } uniquement ; identité portée par Authorization.
    const msg = (rawInput ?? input).trim();
    if (!msg || loading || !token) return;
    if (!rawInput) setInput("");
    setLines((prev) => [...prev, { who: "user", text: msg }]);
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: msg }),
      });
      if (r.status === 401) {
        logout();
        setLines((prev) => [
          ...prev,
          {
            who: "bot",
            text: "Session expirée ou token invalide. Merci de te reconnecter.",
            intent: "auth_expired",
          },
        ]);
        return;
      }
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || r.statusText);
      }
      const data = (await r.json()) as {
        reply: string;
        intent: string;
        needs_confirmation?: boolean;
      };
      const courses = parseCoursesFromReply(data.reply);
      setLines((prev) => [
        ...prev,
        {
          who: "bot",
          text: data.reply,
          courses: courses.length ? courses : undefined,
          intent: data.intent,
          needsConfirmation: Boolean(data.needs_confirmation),
        },
      ]);
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e);
      setLines((prev) => [
        ...prev,
        {
          who: "bot",
          text: `Erreur réseau : ${err}. Lance l'API (Docker ou uvicorn) sur ${API_BASE}.`,
          intent: "client_error",
        },
      ]);
      setBackendStatus("offline");
    } finally {
      setLoading(false);
    }
    },
    [input, loading, token, logout],
  );

  const clearConversation = useCallback(() => {
    const start = [{ who: "bot" as const, text: WELCOME_MESSAGE }];
    setLines(start);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(start));
  }, []);

  return (
    <div className="layout">
      <header className="header">
        <h1>Chatbot horaires — L3GIN</h1>
        <p className="sub">
          Université de Kinshasa, Faculté Polytechnique — assistant conversationnel des horaires
          de cours (FastAPI, PostgreSQL, n8n).
        </p>
        <div className={`backend ${backendStatus}`}>
          {backendStatus === "checking" && "Vérification du backend..."}
          {backendStatus === "online" && "Backend connecté"}
          {backendStatus === "offline" && "Backend indisponible (vérifie Docker/API)"}
        </div>
        {!token && (
          <>
            <div className="auth-tabs">
              <button
                type="button"
                className={authMode === "login" ? "active" : ""}
                onClick={() => setAuthMode("login")}
              >
                Se connecter
              </button>
              <button
                type="button"
                className={authMode === "register" ? "active" : ""}
                onClick={() => setAuthMode("register")}
              >
                Créer un compte
              </button>
            </div>

            {authMode === "login" && (
              <div className="auth-box">
                <label className="sr-only" htmlFor="email-login">
                  Adresse e-mail
                </label>
                <input
                  id="email-login"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email"
                />
                <label className="sr-only" htmlFor="password-login">
                  Mot de passe
                </label>
                <input
                  id="password-login"
                  value={password}
                  type="password"
                  autoComplete="current-password"
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="mot de passe"
                />
                <button type="button" onClick={() => void login()}>
                  Se connecter
                </button>
                {authError && <p className="auth-error">Connexion échouée : {authError}</p>}
              </div>
            )}

            {authMode === "register" && (
              <div className="register-box">
                <label className="sr-only" htmlFor="email-register">
                  Adresse e-mail
                </label>
                <input
                  id="email-register"
                  autoComplete="username"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="email"
                />
                <label className="sr-only" htmlFor="password-register">
                  Mot de passe
                </label>
                <input
                  id="password-register"
                  value={regPassword}
                  type="password"
                  autoComplete="new-password"
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="mot de passe (6 caractères min.)"
                />
                <label className="sr-only" htmlFor="groupe-register">
                  Groupe / promotion
                </label>
                <input
                  id="groupe-register"
                  value={regGroupe}
                  onChange={(e) => setRegGroupe(e.target.value)}
                  placeholder="groupe (ex. L3GIN)"
                />
                <button type="button" onClick={() => void register()}>
                  Créer mon compte
                </button>
                {registerError && (
                  <p className="auth-error">Inscription échouée : {registerError}</p>
                )}
              </div>
            )}
          </>
        )}
        {token && authUser && (
          <div className="session">
            Connecté: <strong>{authUser.email}</strong> ({authUser.role}
            {authUser.groupe ? ` - ${authUser.groupe}` : ""})
            <button type="button" onClick={logout}>
              Logout
            </button>
          </div>
        )}
        <div className="actions">
          <button type="button" onClick={clearConversation}>
            Réinitialiser la conversation
          </button>
        </div>
      </header>
      <main className="chat">
        <div className="messages">
          {lines.map((l, i) => (
            <div key={i} className={`bubble ${l.who}`}>
              {l.text}
              {l.who === "bot" && (l.intent || l.needsConfirmation) && (
                <div className="bubble-meta" aria-label="Détail technique de la réponse">
                  {l.intent && (
                    <span className="intent-tag" title="Intention détectée côté serveur">
                      intent : {l.intent}
                    </span>
                  )}
                  {l.needsConfirmation && (
                    <span className="confirm-badge" title="Le bot attend une confirmation (oui / non)">
                      confirmation
                    </span>
                  )}
                </div>
              )}
              {l.who === "bot" && l.courses && l.courses.length > 0 && (
                <div className="course-cards">
                  {l.courses.map((c, idx) => (
                    <article key={`${c.matiere}-${idx}`} className="course-card">
                      <div className="line">
                        <strong>{c.matiere}</strong> <span>({c.type})</span>
                      </div>
                      <div className="line">{c.horaire}</div>
                      <div className="line">Salle {c.salle}</div>
                      <div className="line">{c.enseignant}</div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="suggestions">
          {suggestions.map((s) => (
            <button key={s} type="button" disabled={loading || !token} onClick={() => void send(s)}>
              {s}
            </button>
          ))}
        </div>
        <div className="composer">
          <label className="sr-only" htmlFor="chat-input">
            Message au chatbot
          </label>
          <textarea
            id="chat-input"
            rows={2}
            value={input}
            placeholder="Ex. : Quel est mon prochain cours ?"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(input);
              }
            }}
          />
          <button type="button" disabled={loading || !token} onClick={() => void send(input)}>
            {loading ? "…" : "Envoyer"}
          </button>
        </div>
      </main>
    </div>
  );
}
