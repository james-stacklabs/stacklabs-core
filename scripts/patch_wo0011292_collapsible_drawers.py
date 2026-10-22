#!/home/james/stacklabs/.venv/bin/python3
"""
Surgical patch for WO0011292:
Wraps long-winded text in App.tsx (verbatim quotes in 3-Bullet Brief, Editorial Rant, and Collectible Card Backstory/Lore/Scars) inside clean HTML5 <details> collapsibles (closed by default).
"""

from pathlib import Path

APP_TSX = Path("/home/james/stacklabs/apps/faas/src/App.tsx")


def main() -> None:
    text = APP_TSX.read_text(encoding="utf-8")

    # 1. Make verbatimQuote in Sniper 3-Bullet Brief collapsible
    old_quote = """                        {bullet.verbatimQuote && (
                          <div className="text-[11px] text-slate-400 italic border-l border-slate-700 pl-2 mt-0.5">
                            "{bullet.verbatimQuote}"
                          </div>
                        )}"""
    new_quote = """                        {bullet.verbatimQuote && (
                          <details className="mt-1 group">
                            <summary className="text-[10px] font-mono text-slate-400 hover:text-amber-400 cursor-pointer select-none">
                              Verbatim quote
                            </summary>
                            <div className="text-[11px] text-slate-400 italic border-l border-slate-700 pl-2 mt-1.5">
                              "{bullet.verbatimQuote}"
                            </div>
                          </details>
                        )}"""
    if old_quote in text:
        text = text.replace(old_quote, new_quote)

    # 2. Make Editorial Rant Body on Daily Barf tab collapsible
    old_editorial = """                {/* Editorial Rant Body */}
                <div className="bg-[#F5F5F5] dark:bg-[#090B0F]/60 border-l-2 border-amber-500 p-3 rounded-[2px]">
                  <p className="text-xs text-[#212121] dark:text-slate-200 leading-relaxed italic font-sans">
                    "{activeBarfPost.editorial}"
                  </p>
                </div>"""
    new_editorial = """                {/* Collapsible Editorial Rant Body */}
                <details className="bg-[#F5F5F5] dark:bg-[#090B0F]/60 border-l-2 border-amber-500 p-3 rounded-[2px]">
                  <summary className="text-[10px] font-mono font-bold text-amber-400 uppercase cursor-pointer select-none">
                    Read Full Editorial Rant
                  </summary>
                  <p className="text-xs text-[#212121] dark:text-slate-200 leading-relaxed italic font-sans mt-2">
                    "{activeBarfPost.editorial}"
                  </p>
                </details>"""
    if old_editorial in text:
        text = text.replace(old_editorial, new_editorial)

    # 3. Make Collectible Card Backstory, Lore & Scar Tissue collapsible (closed by default)
    old_card_lore = """                  {/* Backstory Bio */}
                  <div className="bg-[#0B0D13] p-3 rounded-xl border border-white/10 flex flex-col gap-1">
                    <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">CANONICAL BACKSTORY</span>
                    <p className="text-slate-200 leading-relaxed font-sans text-xs">
                      {card.bio}
                    </p>
                  </div>

                  {/* Fun Facts & Lore Bullet Points */}
                  <div className="bg-[#0B0D13] p-3 rounded-xl border border-white/10 flex flex-col gap-1.5">
                    <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">VERIFIED LORE & HABITS</span>
                    <ul className="flex flex-col gap-1.5 text-slate-300 text-[11px] leading-snug list-disc pl-4">
                      {card.funFacts.map((fact, fIdx) => (
                        <li key={fIdx}>{fact}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Obsession Trigger & Scar Tissue */}
                  <div className="grid grid-cols-1 gap-2">
                    <div className="bg-[#0B0D13] p-2.5 rounded-xl border border-white/10">
                      <span className="text-[10px] font-mono text-rose-400 uppercase font-bold">OBSESSION TRIGGER: </span>
                      <p className="text-slate-300 mt-0.5 italic leading-snug">"{card.obsessionTrigger}"</p>
                    </div>
                    <div className="bg-[#0B0D13] p-2.5 rounded-xl border border-white/10">
                      <span className="text-[10px] font-mono text-slate-400 uppercase font-bold">SCAR TISSUE: </span>
                      <p className="text-slate-300 mt-0.5 leading-snug">{card.scars}</p>
                    </div>
                  </div>"""

    new_card_lore = """                  {/* Collapsible Backstory, Lore & Scar Tissue (Closed by Default) */}
                  <details className="bg-[#0B0D13] p-3 rounded-xl border border-white/10 group">
                    <summary className="text-[10px] font-mono text-amber-400 uppercase font-bold cursor-pointer select-none flex items-center justify-between">
                      <span>Backstory, Lore & Scar Tissue</span>
                      <span className="text-slate-400 font-normal">Tap to expand</span>
                    </summary>
                    <div className="flex flex-col gap-3 pt-3 mt-2 border-t border-white/10">
                      <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">BACKSTORY</span>
                        <p className="text-slate-200 leading-relaxed font-sans text-xs">{card.bio}</p>
                      </div>
                      <div className="flex flex-col gap-1.5">
                        <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">VERIFIED LORE & HABITS</span>
                        <ul className="flex flex-col gap-1.5 text-slate-300 text-[11px] leading-snug list-disc pl-4">
                          {card.funFacts.map((fact, fIdx) => (
                            <li key={fIdx}>{fact}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="grid grid-cols-1 gap-2">
                        <div className="p-2.5 rounded-lg bg-[#11141E] border border-white/10">
                          <span className="text-[10px] font-mono text-rose-400 uppercase font-bold">OBSESSION TRIGGER: </span>
                          <p className="text-slate-300 mt-0.5 italic leading-snug">"{card.obsessionTrigger}"</p>
                        </div>
                        <div className="p-2.5 rounded-lg bg-[#11141E] border border-white/10">
                          <span className="text-[10px] font-mono text-slate-400 uppercase font-bold">SCAR TISSUE: </span>
                          <p className="text-slate-300 mt-0.5 leading-snug">{card.scars}</p>
                        </div>
                      </div>
                    </div>
                  </details>"""

    if old_card_lore in text:
        text = text.replace(old_card_lore, new_card_lore)

    APP_TSX.write_text(text, encoding="utf-8")
    print("Patched App.tsx with collapsible <details> drawers.")


if __name__ == "__main__":
    main()
