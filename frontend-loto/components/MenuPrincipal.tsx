"use client";
import { useState } from "react";

export default function MenuPrincipal({ onChoix }: { onChoix: (choix: string) => void }) {
  const [loterie, setLoterie] = useState("2"); // Valeur par défaut : Lotto Max

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const valeur = e.target.value;
    setLoterie(valeur);
    onChoix(valeur);
  };

  return (
    <div className="mb-6 flex flex-col items-center">
      <h1 className="text-3xl font-bold mb-4">🎯 AI Générateur de Combinaisons</h1>

      <label htmlFor="loterie" className="mb-2 font-medium">
        Sélectionnez une loterie :
      </label>
      <select
        id="loterie"
        value={loterie}
        onChange={handleChange}
        className="p-2 border border-gray-300 rounded"
      >
        <option value="2">Lotto Max</option>
        <option value="3">Lotto 6/49</option>
        <option value="1">Grande Vie</option>
      </select>
    </div>
  );
}
