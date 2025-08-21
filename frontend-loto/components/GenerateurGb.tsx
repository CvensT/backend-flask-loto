"use client";
import { useState } from "react";

type Combinaison = {
  bloc: number;
  combinaison: number[];
  etoile: boolean;
};

type ApiResponse =
  | {
      ok: true;
      data: Combinaison[];
      echo: { loterie: string; blocs: number };
      source: string;
    }
  | {
      ok: false;
      error: string;
      [key: string]: unknown;
    };

export default function GenerateurGb({ loterieId }: { loterieId: string }) {
  const [resultat, setResultat] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const generer = async () => {
    const base = process.env.NEXT_PUBLIC_API_URL;
    if (!base) {
      setErr("❌ L'URL de l'API n’est pas définie.");
      return;
    }

    setLoading(true);
    setErr(null);
    try {
      const response = await fetch(`${base}/api/generer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ loterie: loterieId, mode: "Gb", blocs: 1 }),
      });

      const data: ApiResponse = await response.json();
      setResultat(data);
    } catch (e: unknown) {
      if (e instanceof Error) {
        console.error(e.message);
      } else {
        console.error("Erreur inconnue", e);
      }
      setErr("Erreur réseau ou serveur.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 rounded border mt-6 shadow">
      <button
        className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded"
        onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
          e.preventDefault();
          generer();
        }}
        disabled={loading}
      >
        {loading ? "Chargement..." : "Générer un bloc Gb"}
      </button>

      {err && <p className="text-red-600 mt-3">{err}</p>}

      {resultat && "ok" in resultat && resultat.ok && (
        <div className="mt-5 space-y-4">
          {(resultat.data as Combinaison[]).map((item: Combinaison, idx: number) => (
            <div key={idx} className="bg-gray-100 rounded px-3 py-2">
              <strong>Bloc {item.bloc}</strong> :{" "}
              {item.combinaison.map((n) => n.toString().padStart(2, "0")).join(" ")}
              {item.etoile && <span className="text-yellow-600 font-bold"> ★</span>}
            </div>
          ))}
        </div>
      )}

      {resultat && "ok" in resultat && !resultat.ok && (
        <p className="text-red-500 mt-4">❌ Erreur : {resultat.error}</p>
      )}
    </div>
  );
}
