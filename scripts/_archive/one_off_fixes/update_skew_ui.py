import re

file_path = '/home/james/stacklabs/01_Sovereign_Portal/src/components/TheSkewStudio.tsx'
with open(file_path, 'r') as f:
    content = f.read()

# I want to add some lucide icons if they aren't there
import_line = "import { AlertOctagon, Radio, TrendingUp, AlertTriangle, Sparkles, ClipboardCopy, X, MessageSquare, BarChart2, Activity, LayoutDashboard, MoreHorizontal } from 'lucide-react';"
content = re.sub(r"import { AlertOctagon.*?from 'lucide-react';", import_line, content)


new_ui = """  return (
    <div className={`relative w-full h-[85vh] overflow-hidden rounded-2xl transition-all duration-1000 flex flex-col font-sans ${isMeltingDown ? 'bg-[#1a0505] shadow-[0_0_100px_rgba(255,0,0,0.5)]' : 'bg-[#0B0E14] shadow-2xl'}`}>
       
       {/* Top Nav Header */}
       <div className="flex justify-between items-center px-6 py-4 border-b border-white/5 bg-black/20 shrink-0">
           <div className="flex items-center gap-4">
              <div className="font-display font-black text-2xl tracking-widest text-white flex items-center gap-2">
                 THE SKEW 
                 <span className="text-blue-500 italic text-3xl font-bold -ml-1">S</span>
              </div>
              <div className="text-slate-400 text-xs font-bold tracking-widest uppercase border-l border-white/20 pl-4">AI Sports Panel</div>
           </div>
           <div className="flex items-center gap-8 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
               <div className="flex flex-col items-center gap-1 cursor-pointer hover:text-white"><LayoutDashboard size={16}/> Dashboard</div>
               <div className="flex flex-col items-center gap-1 cursor-pointer hover:text-white"><BarChart2 size={16}/> Stats</div>
               <div className="flex flex-col items-center gap-1 cursor-pointer text-blue-400"><MessageSquare size={16}/> Debates</div>
               <div className="flex flex-col items-center gap-1 cursor-pointer hover:text-white"><MoreHorizontal size={16}/> More</div>
           </div>
       </div>

       {/* Producer Controls Overlay (Hidden by default, hover to show or keep small in corner) */}
       <div className="absolute top-20 right-6 z-50 flex flex-col gap-2 opacity-20 hover:opacity-100 transition-opacity">
           <button onClick={() => window.history.back()} className="px-3 py-1 bg-black/50 border border-white/20 text-white/50 hover:bg-red-600 hover:text-white text-[10px] rounded"><X size={12} /></button>
           <button onClick={() => setIsBuildingRoom(true)} className="px-3 py-1 bg-black/50 border border-white/20 text-white/50 hover:bg-blue-600 hover:text-white text-[10px] rounded">Edit</button>
           <button onClick={() => setIsMeltingDown(!isMeltingDown)} className="px-3 py-1 bg-black/50 border border-white/20 text-white/50 hover:bg-red-600 hover:text-white text-[10px] rounded">Meltdown</button>
       </div>

       <div className="flex-1 flex flex-col p-6 gap-6 overflow-hidden relative z-10">
           {/* Title Bar */}
           <div className="flex justify-between items-center bg-white/5 border border-white/10 rounded-xl px-4 py-3 shrink-0">
              <div className="text-white font-bold tracking-widest uppercase text-sm">LIVE BROADCAST</div>
              <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-white rounded flex items-center justify-center text-black text-lg shadow-[0_0_15px_rgba(255,255,255,0.3)]">
                     {hotTopic.toLowerCase().includes('nfl') ? '��' : hotTopic.toLowerCase().includes('nba') ? '🏀' : '⚾'}
                  </div>
                  <div className="text-white font-bold tracking-widest uppercase text-sm">{hotTopic}</div>
              </div>
              <div className="bg-[#FF5910] text-black px-4 py-1.5 rounded font-black text-[10px] uppercase tracking-widest flex items-center gap-2 shadow-[0_0_15px_rgba(255,89,16,0.5)]">
                  <div className="w-2 h-2 bg-black rounded-full animate-pulse"></div> LIVE
              </div>
           </div>

           {/* Main Stage - Cards */}
           <div className="relative flex justify-center items-end gap-4 py-4 min-h-[220px] shrink-0">
               {panelists.map((panelist, idx) => {
                   const isSpeaking = activeSpeaker === panelist.id;
                   const avatarKeyRaw = panelist.name.toLowerCase();
                   const avatarKeyStripped = avatarKeyRaw.replace(/[\s_]/g, '');
                   //@ts-ignore
                   const avatarUrl = avatarMap[avatarKeyRaw] || avatarMap[avatarKeyStripped] || `/api/persona_image/${avatarKeyRaw}`;
                   const confidence = Math.floor(Math.random() * 20) + 70; // Fake stat for mockup
                   const act = Math.floor(Math.random() * 20) + 75; // Fake stat
                   
                   return (
                       <motion.div 
                          key={panelist.id}
                          animate={{ y: isSpeaking ? -15 : 0, scale: isSpeaking ? 1.05 : 1 }}
                          className={`relative w-36 h-48 rounded-xl border-2 flex flex-col items-center p-3 transition-all duration-300 overflow-hidden ${
                             isSpeaking 
                             ? 'border-[#FF5910] shadow-[0_0_30px_rgba(255,89,16,0.3)] bg-gradient-to-b from-black/80 to-[#FF5910]/20 z-20' 
                             : 'border-[#3B82F6]/40 shadow-lg bg-gradient-to-b from-black/80 to-[#3B82F6]/10 z-10'
                          }`}
                       >
                           {isSpeaking && (
                               <div className="absolute -top-3 bg-red-600 text-white text-[9px] font-bold px-2 py-0.5 rounded uppercase tracking-widest z-30 shadow-[0_0_10px_red]">On Air</div>
                           )}
                           
                           {/* Decorative background wave */}
                           <div className="absolute inset-0 opacity-20 pointer-events-none">
                              <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
                                  <path d="M0,50 Q25,30 50,50 T100,50 L100,100 L0,100 Z" fill="none" stroke={isSpeaking ? '#FF5910' : '#3B82F6'} strokeWidth="1" className={isSpeaking ? 'animate-pulse' : ''}/>
                              </svg>
                           </div>

                           <div className="w-full text-center mb-2 z-10">
                               <div className="text-white font-bold text-[10px] uppercase tracking-widest truncate">{panelist.name}</div>
                               <div className={`text-[8px] flex items-center justify-center gap-1 ${isSpeaking ? 'text-[#FF5910]' : 'text-[#3B82F6]'}`}>
                                   <div className={`w-1.5 h-1.5 rounded-full ${isSpeaking ? 'bg-[#FF5910]' : 'bg-[#3B82F6]'}`}></div> {panelist.alias}
                               </div>
                           </div>
                           
                           <div className="w-20 h-20 rounded-full border border-white/20 overflow-hidden mb-auto z-10 bg-slate-800 shadow-inner">
                               <img src={avatarUrl} alt={panelist.name} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.src = `https://api.dicebear.com/7.x/initials/svg?seed=${panelist.name}&backgroundColor=0f172a&textColor=ffffff`; }} />
                           </div>
                           
                           <div className="w-full flex justify-between items-end mt-2 z-10 border-t border-white/10 pt-2">
                               <div className="flex flex-col">
                                   <span className="text-[8px] text-white/50 uppercase tracking-widest font-bold">Confidence</span>
                                   <div className="w-12 h-1 bg-white/20 rounded mt-1 overflow-hidden">
                                       <div className={`h-full ${isSpeaking ? 'bg-[#FF5910]' : 'bg-[#3B82F6]'}`} style={{ width: `${confidence}%` }}></div>
                                   </div>
                               </div>
                               <div className="flex flex-col items-end">
                                   <span className="text-[8px] text-white/50 uppercase tracking-widest font-bold">Act</span>
                                   <span className={`text-xs font-bold ${isSpeaking ? 'text-[#FF5910]' : 'text-[#3B82F6]'}`}>{act}</span>
                               </div>
                           </div>
                       </motion.div>
                   );
               })}
               
               {/* Desk Graphic */}
               <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80%] h-12 border-t-[3px] border-[#3B82F6] bg-gradient-to-b from-[#3B82F6]/20 to-transparent rounded-t-[100%] flex justify-center items-start pt-2 -z-10 pointer-events-none">
                   <div className="w-12 h-8 bg-white/10 backdrop-blur-md rounded border border-white/20 flex items-center justify-center text-2xl shadow-[0_0_20px_rgba(59,130,246,0.3)]">
                      {hotTopic.toLowerCase().includes('nfl') ? '🏈' : hotTopic.toLowerCase().includes('nba') ? '🏀' : '⚾'}
                   </div>
               </div>
           </div>

           {/* Bottom Split Section */}
           <div className="flex gap-6 flex-1 min-h-0">
               {/* Chat Section */}
               <div className="flex-1 bg-white/5 border border-white/10 rounded-2xl flex flex-col overflow-hidden backdrop-blur-sm">
                   <div className="flex justify-between items-center p-4 border-b border-white/10 shrink-0 bg-black/20">
                       <div className="text-white font-bold text-sm uppercase tracking-widest">LIVE STREAMING CHAT</div>
                       <div className="flex gap-2">
                           <div className="bg-yellow-500/20 text-yellow-500 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest flex items-center gap-1"><div className="w-1.5 h-1.5 bg-yellow-500 rounded-full"></div> LIVE</div>
                           <Activity size={14} className="text-white/50" />
                       </div>
                   </div>
                   
                   <div className="flex-1 p-4 overflow-y-auto custom-scrollbar flex flex-col gap-4">
                       <AnimatePresence initial={false}>
                           {messages.map((msg) => {
                               const avatarKeyRaw = msg.author.toLowerCase();
                               const avatarKeyStripped = avatarKeyRaw.replace(/[\s_]/g, '');
                               //@ts-ignore
                               const avatarUrl = avatarMap[avatarKeyRaw] || avatarMap[avatarKeyStripped] || `/api/persona_image/${avatarKeyRaw}`;
                               const isPanelist = panelists.some(p => p.id === msg.author || p.name === msg.author);
                               
                               return (
                                   <motion.div 
                                      key={msg.id}
                                      initial={{ opacity: 0, x: -20 }}
                                      animate={{ opacity: 1, x: 0 }}
                                      className="flex gap-3"
                                   >
                                       <div className="w-10 h-10 rounded-full shrink-0 border border-white/20 overflow-hidden bg-slate-800">
                                            <img src={avatarUrl} className="w-full h-full object-cover" onError={(e) => { e.currentTarget.src = `https://api.dicebear.com/7.x/initials/svg?seed=${msg.author}&backgroundColor=0f172a&textColor=ffffff`; }} />
                                       </div>
                                       <div className={`flex-1 p-3 rounded-xl rounded-tl-none border backdrop-blur-md ${isPanelist ? 'bg-[#3B82F6]/10 border-[#3B82F6]/30 shadow-[0_0_15px_rgba(59,130,246,0.1)]' : 'bg-white/5 border-white/10'}`}>
                                           <div className="flex justify-between items-center mb-1">
                                               <div className={`text-[10px] font-bold uppercase tracking-widest ${isPanelist ? 'text-[#3B82F6]' : 'text-white/70'}`}>{msg.author}</div>
                                               <div className="text-[9px] text-white/30 font-mono">{new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                                           </div>
                                           <div className="text-sm text-white/90 leading-relaxed font-sans">{msg.text}</div>
                                       </div>
                                   </motion.div>
                               );
                           })}
                       </AnimatePresence>
                   </div>
                   
                   <div className="p-4 border-t border-white/10 shrink-0 bg-black/20">
                       <form onSubmit={(e) => {
                           e.preventDefault();
                           if (!userChatInput.trim() || !wsRef.current) return;
                           wsRef.current.send(JSON.stringify({ type: 'CHAT_MESSAGE', user: 'Guest User', text: userChatInput, target_game_pk: 'the_skew' }));
                           setUserChatInput('');
                       }} className="flex items-center gap-3 bg-black/50 border border-white/20 rounded-full px-4 py-2">
                           <span className="text-white/50 font-bold">+</span>
                           <input 
                              type="text" 
                              value={userChatInput}
                              onChange={e => setUserChatInput(e.target.value)}
                              placeholder="Type a message..." 
                              className="flex-1 bg-transparent border-none text-white text-sm outline-none placeholder-white/30"
                           />
                           <button type="submit" disabled={!userChatInput.trim()} className="text-[#3B82F6] disabled:opacity-50 hover:text-blue-400">
                               <TrendingUp size={16} />
                           </button>
                       </form>
                   </div>
               </div>

               {/* Stats & Info Section */}
               <div className="w-72 flex flex-col gap-4 shrink-0">
                   {/* Live Stats */}
                   <div className="bg-white/5 border border-white/10 rounded-2xl p-5 backdrop-blur-sm flex-1">
                       <div className="text-white font-bold text-sm uppercase tracking-widest mb-6">LIVE STATS</div>
                       <div className="flex flex-col gap-5">
                           <div className="flex gap-3">
                               <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center text-white/50"><TrendingUp size={16}/></div>
                               <div>
                                   <div className="text-white text-xs font-bold">Engagement Rate</div>
                                   <div className="text-white/50 text-[10px]">98.2% Active</div>
                               </div>
                           </div>
                           <div className="flex gap-3">
                               <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center text-white/50"><BarChart2 size={16}/></div>
                               <div>
                                   <div className="text-white text-xs font-bold">Sentiment</div>
                                   <div className="text-[#FF5910] text-[10px] font-bold">Highly Volatile</div>
                               </div>
                           </div>
                           <div className="flex gap-3">
                               <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center text-white/50"><Activity size={16}/></div>
                               <div>
                                   <div className="text-white text-xs font-bold">Boggs Level</div>
                                   <div className="text-red-500 text-[10px] font-bold animate-pulse">Critical</div>
                               </div>
                           </div>
                       </div>
                   </div>

                   {/* Game Feed */}
                   <div className="bg-white/5 border border-white/10 rounded-2xl p-5 backdrop-blur-sm flex-1">
                       <div className="flex justify-between items-center mb-4">
                          <div className="text-white font-bold text-sm uppercase tracking-widest">TOPIC FEED</div>
                          <span className="text-white/50 text-[10px]">^</span>
                       </div>
                       <div className="flex flex-col gap-3 relative before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
                           <div className="flex gap-3 relative z-10">
                               <div className="w-3 h-3 rounded-full bg-green-500 border-2 border-[#0B0E14] mt-0.5"></div>
                               <div className="text-[10px]">
                                   <span className="text-white font-bold">System:</span> <span className="text-white/50">Panel Initialized</span>
                               </div>
                           </div>
                           <div className="flex gap-3 relative z-10">
                               <div className="w-3 h-3 rounded-full bg-blue-500 border-2 border-[#0B0E14] mt-0.5"></div>
                               <div className="text-[10px]">
                                   <span className="text-white font-bold">Prompt:</span> <span className="text-white/50">Topic Injected</span>
                               </div>
                           </div>
                           <div className="flex gap-3 relative z-10">
                               <div className="w-3 h-3 rounded-full bg-[#FF5910] border-2 border-[#0B0E14] mt-0.5"></div>
                               <div className="text-[10px]">
                                   <span className="text-white font-bold">Warning:</span> <span className="text-white/50">Tension Escalating</span>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
           </div>
       </div>

       {/* Flow Prompt Modal */}
       <AnimatePresence>
           {flowPrompt && (
               <motion.div 
                   initial={{ opacity: 0 }}
                   animate={{ opacity: 1 }}
                   exit={{ opacity: 0 }}
                   className="absolute inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md"
               >
                   <div className="bg-[#0B0E14] border border-blue-500/30 rounded-2xl p-6 w-[600px]">
                       <div className="flex justify-between items-center mb-4">
                           <h3 className="text-blue-400 font-display font-bold uppercase tracking-widest flex items-center gap-2">
                               <Sparkles size={20} /> Director's Prompt
                           </h3>
                           <button onClick={() => setFlowPrompt(null)} className="text-white/50 hover:text-white"><X size={20} /></button>
                       </div>
                       <textarea className="w-full h-48 bg-black border border-white/10 rounded-xl p-4 text-white font-mono text-xs focus:border-blue-500 outline-none" value={flowPrompt} readOnly />
                   </div>
               </motion.div>
           )}
       </AnimatePresence>
    </div>
  );
}
"""

start_idx = content.find("  return (\n    <div className={`relative w-full h-[85vh] overflow-hidden")
if start_idx != -1:
    content = content[:start_idx] + new_ui

with open(file_path, 'w') as f:
    f.write(content)
print("Updated successfully")
