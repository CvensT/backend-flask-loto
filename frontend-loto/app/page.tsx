"use client";
import { useState } from "react";
import MenuPrincipal from "../components/MenuPrincipal";
import GenerateurGb from "../components/GenerateurGb";
import VerificationHistorique from "../components/VerificationHistorique";
import VerificationBlocs from "../components/VerificationBlocs";

type Action = "generer" | "verif" | "verif_blocs";

export default function Page() {
  const [loterieId, setLoterieId] = useState<string>("2");
  const [action, setAction] = useState<Action>("generer");

  return (
    <main className="p-6 max-w-3xl mx-auto">
      <MenuPrincipal onChoix={setLoterieId} />

      <div className="flex justify-center space-x-4 mb-6">
        <button
          className={`py-2 px-4 rounded font-semibold shadow ${
            action === "generer" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => setAction("generer")}
        >
          Générer (Gb)
        </button>

        <button
          className={`py-2 px-4 rounded font-semibold shadow ${
            action === "verif" ? "bg-green-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => setAction("verif")}
        >
          Vérifier combinaisons (V)
        </button>

        <button
          className={`py-2 px-4 rounded font-semibold shadow ${
            action === "verif_blocs" ? "bg-yellow-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => setAction("verif_blocs")}
        >
          Vérifier blocs (Vb)
        </button>
      </div>

      {action === "generer" && <GenerateurGb loterieId={loterieId} />}
      {action === "verif" && <VerificationHistorique loterieId={loterieId} />}
      {action === "verif_blocs" && <VerificationBlocs loterieId={loterieId} />}
    </main>
  );
}

