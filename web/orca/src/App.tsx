import { Helmet } from "react-helmet";
import React, { useCallback, useEffect, useRef, useState } from "react";
import styles from "./App.module.css";
import Sidebar1 from "./components/Sidebar1";
import { Button, Img, TextArea, Heading, Input,Text } from "./components";
import MarketingText from "./components/MarketingText";
import { Chat, ChatEntry, ChatResponse, ResponseChunk } from "./components/interfaces";
import ReactMarkdown from "react-markdown";
import Markdown from 'markdown-to-jsx';
import Citation, { getPDFLinks, openPDFAtBestMatch } from "./components/Citation";
import RelatedQuestion from "./components/RelatedQuestion/relatedQuestion";
import CopyIcon from "./components/CopyIcon/copy";
import { selectOptionType } from "./components/SelectBox";
import StopIcon from "./components/Icons/StopIcon";
import SendIcon from "./components/Icons/SendIcon";
import remarkGfm from 'remark-gfm';
import DeepResearch from './components/Icons/DeepResearch';
import LoadingDots from './components/LoadingDots';


const App = () => {

    const [prompt, updatePrompt] = useState<string>("");
    const [input, setInput] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [chats, setChats] = useState<{ [key: string]:Chat }>(() => {
      const savedChats = localStorage.getItem('chats');
      const newChatId = `chat-${Date.now()}`;
      return savedChats ? JSON.parse(savedChats) : {[newChatId] : {chatEntries: [], title:"New Chat"}};
    });
    const [abortController, setAbortController] = useState<AbortController | null>(null);
    const [citationsInfo,setCitationsInfo] = useState<string>("");
    const [openSources, setOpenSources] = useState<{ [key: number]: boolean }>({});
    const [chatId, setChatId] = useState<string>(Object.keys(chats)[0]);
    const [currentAnswer, setCurrentAnswer] = useState<string>("");
    const [loggedIn, setLoggedIn] = useState<boolean>(false);
    const [username, setUsername] = useState<string>("");
    const [isSideBarOpen, setSideBarOpen] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    //const [category, setCategory] = useState<selectOptionType | null>(null);
    const [isCopied, setIsCopied] = useState(false);
    const [theme, setTheme] = useState("light");
    const [mode, setMode] = useState<'answer' | 'report'>('answer');

    useEffect(() => {
        let timeoutId:number;
        if (isCopied) {
          timeoutId = setTimeout(() => setIsCopied(false), 3000);
        }
        return () => clearTimeout(timeoutId);
      }, [isCopied]);
  
    useEffect(() => {
      scrollToBottom();
    }, [currentAnswer]);
  
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };
    
    const fetchData = useCallback(async () => {
        let newAnswer = "";
        let newCitations = "";
        let relatedQns: string[] = [];
        if (prompt.trim() === "") {
          return;
        }
        try {
            setLoading(true);
            setCurrentAnswer("");
            const controller = new AbortController();
            setAbortController(controller);
            const requestBody = JSON.stringify({
              "chat_id": chatId,
              "message": prompt,
              "metadata" : {}
              //category: "oil_gas",
              //file_name: "",
              //collection_name: "documents",
              //persist_dir: "v6_persist"
              });
            const endpoint = mode === 'answer' ? 'v1/chat' : 'v1/report';
            // Same-origin relative path: nginx proxies /v1/ -> retrieval_api:8080
            // so the request rides the same (preview) URL the page is served from.
            const response = await fetch(`/${endpoint}`, {
                    method: "post",
                    headers: {
                    "Content-Type": "application/json",
                    },
                    body: requestBody,
                    signal: controller.signal,
            });
            if (!response.ok) {
                const error = await response.text();
                throw new Error(`Failed (${response.status}): ${error}`,);
            };
            // if (!body.stream) { // the non-streaming case
            //   return response.json();
            // }
            if (!response.ok || !response.body) {
                throw response.statusText;
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let count = 0;
            let braceCount = 0;
            let jsonStart = -1;
            // Add heading for report mode
            if (mode === 'report') {
                newAnswer = "# Generated Report\n\n";
            }
            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                break;
                }
                const decodedChunk = decoder.decode(value, { stream: true });
                //console.log(decodedChunk);
                
                buffer += decodedChunk;
                
                count += 1;

                     
                // let startIndex = buffer.indexOf('{');
                // let endIndex = buffer.indexOf('}');

                // //newAnswer += decodedChunk;
                // let updateCount = 0;
                // let index = 0;
                // console.log("start index " + startIndex);
                // console.log(endIndex);
                // console.log(buffer);
                // while (startIndex != -1 && endIndex != -1) {
                //     console.log(count + " c " + reachedAnswer + " " + citationsParsed);
                //     if(reachedAnswer && !citationsParsed){
                //         console.log("121 " + buffer);
                //         if(buffer.indexOf(`}"}`) == -1){
                //           break;
                //         }
                //         console.log(buffer.indexOf(`}"`,index));
                //         while(buffer.indexOf(`}"`,index)!= -1){
                //             index = buffer.indexOf(`}"`,index)+1;
                //         }
                //         endIndex = buffer.indexOf("}",index);
                //         const jsonString = buffer.slice(startIndex, endIndex + 1);
                //         try {
                //           const res: ChatResponse = JSON.parse(jsonString);
                //           if (res.type == "context") {
                //             citationsParsed = 1;
                //             newCitations = res.text;
                //           }
                //         }catch (e) {
                //           // If JSON.parse fails, break out of the loop and wait for more data
                //             console.log("error parsing citations" + e);
                //             alert("Parsing failed");
                //             break;
                //           }
                //         buffer = buffer.slice(endIndex + 1);
                //         endIndex = buffer.indexOf('}');
                //     }else if(!reachedAnswer){
                //         const jsonString = buffer.slice(startIndex, endIndex + 2);
                //         console.log("response: " + jsonString);
                //         try {
                //           const res: ChatResponse = JSON.parse(jsonString);
                //           //console.log(res);
                //           if (res.type === 'tokens' || res.type === 'greeting' || res.type === 'error') {
                //               newAnswer += res.text;
                //               updateCount += 1;
                //               await new Promise(resolve => setTimeout(resolve, 10));
                //               console.log(updateCount);
                //           } else if (res.type == 'answer') {
                //               reachedAnswer = 1;
                //               newAnswer = res.text;
                //               //setCurrentAnswer(res.text);
                //           }else if(res.type == "related") {
                //               relatedQns.push(res.text);
                //           }
                //           setCurrentAnswer(newAnswer);
                //           // Move the buffer forward, past the parsed JSON object
                //           buffer = buffer.slice(endIndex + 1);
                //         //console.log(buffer);
                //         }catch (e) {
                //         // If JSON.parse fails, break out of the loop and wait for more data
                //           console.log("error parsing answer or tokens" + e);
                //           break;
                //         }
                //         endIndex = buffer.indexOf('}');
                //     }else {
                //         const jsonString = buffer.slice(startIndex, endIndex + 1);
                //         //console.log(jsonString);
                //         try {
                //           const res: ChatResponse = JSON.parse(jsonString);
                //           //console.log(res);
                //           if(res.type == "related") {
                //               relatedQns.push(res.text);
                //           }
                //           setCurrentAnswer(newAnswer);
                //           // Move the buffer forward, past the parsed JSON object
                //           buffer = buffer.slice(endIndex + 1);
                //         //console.log(buffer);
                //         }catch (e) {
                //         // If JSON.parse fails, break out of the loop and wait for more data
                //           console.log("error parsing related" + e);
                //           break;
                //         }
                //         endIndex = buffer.indexOf('}');

                //     }

                    
                    

                //     // Update startIndex and endIndex for the next loop iteration
                //     startIndex = buffer.indexOf('{');
                // }
  
            }
            for (let i = 0; i < buffer.length; i++) {
              //console.log("Buffer ", buffer);
              const char = buffer[i];
    
              if (char === "{") {
                if (braceCount === 0) {
                  jsonStart = i;
                }
                braceCount++;
              } else if (char === "}") {
                braceCount--;
    
                if (braceCount === 0 && jsonStart !== -1) {
                  const jsonString = buffer.substring(jsonStart, i + 1);
                  try {
                    const chunk: ResponseChunk = JSON.parse(jsonString);
                    if (["greeting", "tokens", "error"].includes(chunk.type)) {
                      newAnswer += chunk.text;
                    }
                    if(chunk.type=="context"){
                      console.log("context text: ",chunk.text)
                      if(chunk.text != "{}"){
                        newCitations = chunk.text;
                      }
                    }
                    if(chunk.type=="answer"){
                      newAnswer = chunk.text;
                    }
                    if(chunk.type=="related"){
                      relatedQns.push(chunk.text);
                    }
                    // if(chunk.type=="title"){
                    //   relatedQns.push(chunk.text);
                    // }
                  } catch (err) {
                    console.error("Failed to parse JSON:", err);
                  }
    
                  // Move buffer ahead
                  buffer = buffer.slice(i + 1);
                  i = -1; // Restart loop at beginning of new buffer
                  jsonStart = -1;
                }
              }
            }           
            setChats((prevChats) => {
                console.log("New");
                const updatedChats = { ...prevChats };
                if (!updatedChats[chatId]) {
                    updatedChats[chatId] = {
                    chatEntries: [],
                    title: 'New Chat',
                    };
                }
                updatedChats[chatId].chatEntries = [...updatedChats[chatId].chatEntries, { 
                    user: prompt, 
                    bot: newAnswer, 
                    citations: newCitations, 
                    related: relatedQns,
                    mode: mode
                }]; 
                localStorage.setItem('chats', JSON.stringify(updatedChats));
                return updatedChats;
            });
        } catch (err) {
          if (err === 'AbortError') {
            console.log('Fetch aborted');
          } else {
            console.error(err, "err");
          }
        } finally {
            setLoading(false);
            updatePrompt("");
            setAbortController(null);
        }
      }, [prompt]);
    
    useEffect(() => {
      if (loading) {
        fetchData();
      }
    }, [loading]);
    // const changeCategory = (option: selectOptionType) =>{
    //     console.log("changing categoty");
    //     setCategory(option);
    // }
    const startNewChat = useCallback(() => {
      if (loading) return; // Prevent new chat creation while loading
      
      const lenChats = Object.keys(chats).length;
      const newChatId = `chat-${Date.now()}`;
      setChats((prevChats) => {
        const updatedChats = {...prevChats}
        updatedChats[newChatId] = {chatEntries: [], title: `New Chat ${Object.keys(updatedChats).length + 1}`};
        localStorage.setItem('chats', JSON.stringify(updatedChats));
        return updatedChats;
      })
      
      setChatId(newChatId);
      updatePrompt("");
      setCurrentAnswer("");
    }, [loading]);
  
    const handleLogin = (username: string) => {
      setUsername(username);
      setLoggedIn(true);
    };
    const handleRegenerate = () => {
      console.log("Check Hi");
      const query = chats[chatId].chatEntries[chats[chatId].chatEntries.length - 1].user;
      
      
      setChats((prevChats)=>{
        const updatedChats = { ...prevChats };
        const chatMessages = [...updatedChats[chatId].chatEntries]; // Copy the array
        chatMessages.pop(); // Remove the last entry
        updatedChats[chatId].chatEntries = chatMessages;
        console.log(updatedChats[chatId]); 
        //updatedChats[chatId].pop();
        return updatedChats;
        
      });
      setLoading(true);
    };
    function handleUpdatePromptToRegenerate(chats: { [key: string]: ChatEntry[]; }) {
      const query = chats[chatId][chats[chatId].length - 1].user;
      updatePrompt(query);
    }
  
    const handleSend = () => {
      // if(!category){
      //   alert("please select a category");
      //   return;
      // }
      //updatePrompt(input);
      //setInput("");
      if (prompt.trim() !== "") {
        setLoading(true);
      }
    };
  
    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        updatePrompt(e.target.value);
    };
    const [selectedOption, setSelectedOption] = useState<string>('Finance');
  
    const handleCategoryChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedOption(event.target.value);
    };
    const handleStop = () => {
      if (abortController) {
        abortController.abort();
      }
      setLoading(false);
      setAbortController(null);
    };
    // if (!loggedIn) {
    //   return <Login onLogin={handleLogin} />;
    // }
    const handleCopy = (text: string) => {
      navigator.clipboard.writeText(text).then(() => {
        //alert('Copied to clipboard');
      }).catch(err => {
        console.error('Failed to copy: ', err);
      });
      setIsCopied(true);
    };
    const renameChat = (chatId: string, newTitle: string) => {
        setChats((prevChats) => {
            const updatedChats = { ...prevChats };
            //updatedChats[chatId].push({ user: prompt, bot: newAnswer });
            updatedChats[chatId].title = newTitle;
            localStorage.setItem('chats', JSON.stringify(updatedChats));
            return updatedChats;
        });
    }
    const deleteChat = (chatIdToBeDeleted: string) => {
        setChats((prevChats) => {
          const updatedChats = { ...prevChats };
          delete updatedChats[chatIdToBeDeleted];
          localStorage.setItem('chats', JSON.stringify(updatedChats));
          return updatedChats;
        });
        // If the deleted chat was the current chat, switch to another chat or create a new one
        if (chatIdToBeDeleted === chatId) {
          const remainingChats = Object.keys(chats);
          if (remainingChats.length > 0) {
            setChatId(remainingChats[0]);
          } else {
            startNewChat();
          }
        }
    };
    const handleQuestionClick = (question: string) => {
        updatePrompt(question);
        // if(!category){
        //   alert("please select a category");
        //   return;
        // }
        setLoading(true);
        // Add your logic here to start generating the response
    };
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend();
      }
    }
  return (
    <>
      <Helmet>
        <title>Document Parser</title>
        <meta name="description" content="Web site created using create-react-app" />
      </Helmet>
      <div className={styles.container}>
        {isSideBarOpen && <Sidebar1 chats={chats} 
                  handleThreadChange={(chatId: string) => setChatId(chatId)} 
                  chatId={chatId} newChatHandler={startNewChat} 
                  renameChat={renameChat} 
                  deleteChat={deleteChat}
                  handleCategoryChange={()=> {}}
        />}
        <div className={styles.mainContent}>
          <div className="sticky top-0 z-20 bg-white flex w-full items-center" style={{ minHeight: 60 }}>
              <button
                className="top-0 left-0 z-50 bg-white border border-gray-300 rounded-full p-1 shadow hover:bg-gray-100 transition"
                onClick={() => setSideBarOpen((prev) => !prev)}
                style={{ position: 'relative', top: 0, left: isSideBarOpen ? 2 : 2 }} // adjust left if your sidebar is fixed width
                aria-label={isSideBarOpen ? "Close sidebar" : "Open sidebar"}
              >
                {isSideBarOpen ? (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="icon-xl-heavy max-md:hidden"><path fill-rule="evenodd" clip-rule="evenodd" d="M8.85719 3H15.1428C16.2266 2.99999 17.1007 2.99998 17.8086 3.05782C18.5375 3.11737 19.1777 3.24318 19.77 3.54497C20.7108 4.02433 21.4757 4.78924 21.955 5.73005C22.2568 6.32234 22.3826 6.96253 22.4422 7.69138C22.5 8.39925 22.5 9.27339 22.5 10.3572V13.6428C22.5 14.7266 22.5 15.6008 22.4422 16.3086C22.3826 17.0375 22.2568 17.6777 21.955 18.27C21.4757 19.2108 20.7108 19.9757 19.77 20.455C19.1777 20.7568 18.5375 20.8826 17.8086 20.9422C17.1008 21 16.2266 21 15.1428 21H8.85717C7.77339 21 6.89925 21 6.19138 20.9422C5.46253 20.8826 4.82234 20.7568 4.23005 20.455C3.28924 19.9757 2.52433 19.2108 2.04497 18.27C1.74318 17.6777 1.61737 17.0375 1.55782 16.3086C1.49998 15.6007 1.49999 14.7266 1.5 13.6428V10.3572C1.49999 9.27341 1.49998 8.39926 1.55782 7.69138C1.61737 6.96253 1.74318 6.32234 2.04497 5.73005C2.52433 4.78924 3.28924 4.02433 4.23005 3.54497C4.82234 3.24318 5.46253 3.11737 6.19138 3.05782C6.89926 2.99998 7.77341 2.99999 8.85719 3ZM6.35424 5.05118C5.74907 5.10062 5.40138 5.19279 5.13803 5.32698C4.57354 5.6146 4.1146 6.07354 3.82698 6.63803C3.69279 6.90138 3.60062 7.24907 3.55118 7.85424C3.50078 8.47108 3.5 9.26339 3.5 10.4V13.6C3.5 14.7366 3.50078 15.5289 3.55118 16.1458C3.60062 16.7509 3.69279 17.0986 3.82698 17.362C4.1146 17.9265 4.57354 18.3854 5.13803 18.673C5.40138 18.8072 5.74907 18.8994 6.35424 18.9488C6.97108 18.9992 7.76339 19 8.9 19H9.5V5H8.9C7.76339 5 6.97108 5.00078 6.35424 5.05118ZM11.5 5V19H15.1C16.2366 19 17.0289 18.9992 17.6458 18.9488C18.2509 18.8994 18.5986 18.8072 18.862 18.673C19.4265 18.3854 19.8854 17.9265 20.173 17.362C20.3072 17.0986 20.3994 16.7509 20.4488 16.1458C20.4992 15.5289 20.5 14.7366 20.5 13.6V10.4C20.5 9.26339 20.4992 8.47108 20.4488 7.85424C20.3994 7.24907 20.3072 6.90138 20.173 6.63803C19.8854 6.07354 19.4265 5.6146 18.862 5.32698C18.5986 5.19279 18.2509 5.10062 17.6458 5.05118C17.0289 5.00078 16.2366 5 15.1 5H11.5ZM5 8.5C5 7.94772 5.44772 7.5 6 7.5H7C7.55229 7.5 8 7.94772 8 8.5C8 9.05229 7.55229 9.5 7 9.5H6C5.44772 9.5 5 9.05229 5 8.5ZM5 12C5 11.4477 5.44772 11 6 11H7C7.55229 11 8 11.4477 8 12C8 12.5523 7.55229 13 7 13H6C5.44772 13 5 12.5523 5 12Z" fill="currentColor"></path></svg>
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="icon-xl-heavy max-md:hidden"><path fill-rule="evenodd" clip-rule="evenodd" d="M8.85719 3H15.1428C16.2266 2.99999 17.1007 2.99998 17.8086 3.05782C18.5375 3.11737 19.1777 3.24318 19.77 3.54497C20.7108 4.02433 21.4757 4.78924 21.955 5.73005C22.2568 6.32234 22.3826 6.96253 22.4422 7.69138C22.5 8.39925 22.5 9.27339 22.5 10.3572V13.6428C22.5 14.7266 22.5 15.6008 22.4422 16.3086C22.3826 17.0375 22.2568 17.6777 21.955 18.27C21.4757 19.2108 20.7108 19.9757 19.77 20.455C19.1777 20.7568 18.5375 20.8826 17.8086 20.9422C17.1008 21 16.2266 21 15.1428 21H8.85717C7.77339 21 6.89925 21 6.19138 20.9422C5.46253 20.8826 4.82234 20.7568 4.23005 20.455C3.28924 19.9757 2.52433 19.2108 2.04497 18.27C1.74318 17.6777 1.61737 17.0375 1.55782 16.3086C1.49998 15.6007 1.49999 14.7266 1.5 13.6428V10.3572C1.49999 9.27341 1.49998 8.39926 1.55782 7.69138C1.61737 6.96253 1.74318 6.32234 2.04497 5.73005C2.52433 4.78924 3.28924 4.02433 4.23005 3.54497C4.82234 3.24318 5.46253 3.11737 6.19138 3.05782C6.89926 2.99998 7.77341 2.99999 8.85719 3ZM6.35424 5.05118C5.74907 5.10062 5.40138 5.19279 5.13803 5.32698C4.57354 5.6146 4.1146 6.07354 3.82698 6.63803C3.69279 6.90138 3.60062 7.24907 3.55118 7.85424C3.50078 8.47108 3.5 9.26339 3.5 10.4V13.6C3.5 14.7366 3.50078 15.5289 3.55118 16.1458C3.60062 16.7509 3.69279 17.0986 3.82698 17.362C4.1146 17.9265 4.57354 18.3854 5.13803 18.673C5.40138 18.8072 5.74907 18.8994 6.35424 18.9488C6.97108 18.9992 7.76339 19 8.9 19H9.5V5H8.9C7.76339 5 6.97108 5.00078 6.35424 5.05118ZM11.5 5V19H15.1C16.2366 19 17.0289 18.9992 17.6458 18.9488C18.2509 18.8994 18.5986 18.8072 18.862 18.673C19.4265 18.3854 19.8854 17.9265 20.173 17.362C20.3072 17.0986 20.3994 16.7509 20.4488 16.1458C20.4992 15.5289 20.5 14.7366 20.5 13.6V10.4C20.5 9.26339 20.4992 8.47108 20.4488 7.85424C20.3994 7.24907 20.3072 6.90138 20.173 6.63803C19.8854 6.07354 19.4265 5.6146 18.862 5.32698C18.5986 5.19279 18.2509 5.10062 17.6458 5.05118C17.0289 5.00078 16.2366 5 15.1 5H11.5ZM5 8.5C5 7.94772 5.44772 7.5 6 7.5H7C7.55229 7.5 8 7.94772 8 8.5C8 9.05229 7.55229 9.5 7 9.5H6C5.44772 9.5 5 9.05229 5 8.5ZM5 12C5 11.4477 5.44772 11 6 11H7C7.55229 11 8 11.4477 8 12C8 12.5523 7.55229 13 7 13H6C5.44772 13 5 12.5523 5 12Z" fill="currentColor"></path></svg>
                )}
              </button>
              <div className="relative rounded-lg left-2 border border-solid border-slate-300 shadow-md bg-slate-100 p-1">{chats[chatId].title}</div>
          </div>
          <div className={styles.customScrollbar}>
            <div className={`w-[66%] !font-sans flex flex-col items-center justify-center gap-8 overflow-y-auto -z-10 mx-auto`}>
                {chats[chatId] && chats[chatId].chatEntries?.length > 0 ? chats[chatId].chatEntries.map((chat, index) =>{
                    return (
                        <div key={index} className="w-[100%]">
                            <div className={`ml-auto pl-5 pr-2 py-2.5 mb-10 max-w-[60%] w-fit text-left text-pretty rounded-3xl bg-slate-300 rounded-se-lg`}>
                                {chat.user}
                            </div>
                            <div className="flex flex-col gap-6 self-stretch">
                                <div className="flex flex-col gap-2 max-w-[90%]  w-fit">
                                    <div className={`rounded-lg ${styles.textArea}`}>
                                    <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                p: ({ children }) => <p className="mb-2">{children}</p>,
                                h1: ({ children }) => <h1 className="text-xl font-bold mb-2">{children}</h1>,
                                h2: ({ children }) => <h2 className="text-lg font-bold mb-2">{children}</h2>,
                                h3: ({ children }) => <h3 className="text-base font-bold mb-2">{children}</h3>,
                                em: ({ children }) => <i>{children}</i>,
                                strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                                ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                                ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                                li: ({ children }) => <li className="mb-1">{children}</li>,
                                code: ({ node, className, children, ...props }) => {
                                  const match = /language-(\w+)/.exec(className || '');
                                  return match ? (
                                    <pre className={`bg-gray-100 rounded p-2 mb-2 overflow-x-auto ${ 'bg-gray-800 text-gray-300'}`}>
                                      <code className={className} {...props}>
                                        {children}
                                      </code>
                                    </pre>
                                  ) : (
                                    <code className={`bg-gray-100 rounded px-1 ${'bg-gray-800 text-gray-300'}`} {...props}>
                                      {children}
                                    </code>
                                  );
                                },
                                a: ({ href, children }) => {
                                  // Handle citation-style links
                                  console.log(children);
                                  const citationMatch = children?.toString().match(/^\[\[?(\d+)\]\]?$/);
                                  console.log(citationMatch);
                                  if (citationMatch) {
                                    const citationNumber = citationMatch[1];
                                    console.log(citationNumber);
                                    return (
                                      <a 
                                        className="text-blue-500 hover:underline cursor-pointer" 
                                        onClick={() => {
                                          if(getPDFLinks(chat.citations).length <= 0) return;
                                          const citations = getPDFLinks(chat.citations)[parseInt(citationNumber) - 1];
                                          //openPDFAtBestMatch(citations.pdfURL, citations.pageNum);
                                          window.open(`${citations.pdfURL}#page=${citations.pageNum}`, '_blank')
                                        }}
                                      >
                                        [{citationNumber}]
                                      </a>
                                    );
                                  }
                                  // Handle regular links
                                  return (
                                    <a 
                                      href={href} 
                                      className="text-blue-500 hover:underline cursor-pointer" 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                    >
                                      {children}
                                    </a>
                                  );
                                },
                                // Add a custom component for handling citations
                                text: ({ children }) => {
                                  const text = children?.toString() || '';
                                  // Replace citation patterns with clean citations
                                  const processedText = text.replace(/\[\[?(\d+)\]\]?\([^)]*\)/g, '[$1]');
                                  return <>{processedText}</>;
                                },
                                table: ({ children }) => (
                                  <table className="min-w-full bg-white border mb-4 mt-4 border-gray-300">{children}</table>
                                ),
                                thead: ({ children }) => (
                                  <thead className="">{children}</thead>
                                ),
                                tbody: ({ children }) => (
                                  <tbody>{children}</tbody>
                                ),
                                tr: ({ children }) => (
                                  <tr className="border-b border-gray-300">{children}</tr>
                                ),
                                th: ({ children }) => (
                                  <th className="px-4 py-2 text-left">{children}</th>
                                ),
                                td: ({ children }) => (
                                  <td className="px-4 py-2">{children}</td>
                                ),
                              }}
                            >{chat.bot}</ReactMarkdown>
                            
                                </div>
                                    <CopyIcon textToCopy={chat.bot}></CopyIcon>
                                </div>
                                {chat.citations !== "" && chat.citations !== "{}" && (
                                  <div className="flex flex-col">
                                    <div
                                      className="flex items-center cursor-pointer select-none"
                                      onClick={() =>
                                        setOpenSources((prev) => ({
                                          ...prev,
                                          [index]: !prev[index],
                                        }))
                                      }
                                    >
                                      {/* Toggle Icon */}
                                      <svg
                                        className={`w-4 h-4 mr-2 transition-transform ${openSources[index] ? "rotate-90" : ""}`}
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth={2}
                                        viewBox="0 0 24 24"
                                      >
                                        <path d="M9 5l7 7-7 7" />
                                      </svg>
                                      <div className="font-bold">Sources :</div>
                                    </div>
                                    {openSources[index] && (
                                      <div className="sources">
                                        <Citation key={1} text={"Sources:"} url={""} response={chat.citations} />
                                      </div>
                                    )}
                                  </div>
                                )}
                                
                                {chat.related && chat.related.length>0 && (index == (chats[chatId].chatEntries.length - 1)) &&
                                    <div>
                                        <div className={styles.heading}>
                                            <p className="font-extrabold">Related</p>
                                        </div>
                                        {chat.related.map((question,index) => {
                                            return <RelatedQuestion
                                            onQuestionClick={handleQuestionClick}
                                            question={question}
                                            >

                                            </RelatedQuestion>
                                        }
                                        )}
                                    </div>
                                }
                                
                            </div>
                        </div>
                    )
                }) : <div></div>}
                {loading &&
                    (<div key={1} className="w-[100%]">
                            <div className={`ml-auto pl-5 pr-2 py-2.5 mb-10 max-w-[60%] w-fit text-left text-pretty rounded-3xl bg-slate-300 rounded-se-lg`}>
                                {prompt}
                            </div>
                            {currentAnswer.length>0 &&
                            <div className="flex flex-col gap-6 self-stretch">
                                <div className="flex flex-col gap-2 max-w-[90%]  w-fit">
                                    <div className={styles.textArea} ref={messagesEndRef}><ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                      components={{
                                        p: ({ children }) => <p className="mb-2">{children}</p>,
                                        h1: ({ children }) => <h1 className="text-xl font-bold mb-2">{children}</h1>,
                                        h2: ({ children }) => <h2 className="text-lg font-bold mb-2">{children}</h2>,
                                        h3: ({ children }) => <h3 className="text-base font-bold mb-2">{children}</h3>,
                                        em: ({ children }) => <i>{children}</i>,
                                        strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                                        ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
                                        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
                                        li: ({ children }) => <li className="mb-1">{children}</li>,
                                        code: ({ node, className, children, ...props }) => {
                                          const match = /language-(\w+)/.exec(className || '');
                                          return match ? (
                                            <pre className={`bg-gray-100 rounded p-2 mb-2 overflow-x-auto ${ 'bg-gray-800 text-gray-300'}`}>
                                              <code className={className} {...props}>
                                                {children}
                                              </code>
                                            </pre>
                                          ) : (
                                            <code className={`bg-gray-100 rounded px-1 ${'bg-gray-800 text-gray-300'}`} {...props}>
                                              {children}
                                            </code>
                                          );
                                        },
                                        a: ({ href, children }) => {
                                          // Handle citation-style links
                                          const citationMatch = children?.toString().match(/^\[\[?(\d+)\]\]?$/);
                                          if (citationMatch) {
                                            const citationNumber = citationMatch[1];
                                            return (
                                              <a 
                                                className="text-blue-500 hover:underline cursor-pointer" 
                                                onClick={() => {
                                                  // For current answer, we don't have citations yet
                                                  // This will be handled when the answer is complete
                                                  return;
                                                }}
                                              >
                                                [{citationNumber}]
                                              </a>
                                            );
                                          }
                                          // Handle regular links
                                          return (
                                            <a 
                                              href={href} 
                                              className="text-blue-500 hover:underline cursor-pointer" 
                                              target="_blank" 
                                              rel="noopener noreferrer"
                                            >
                                              {children}
                                            </a>
                                          );
                                        },
                                        table: ({ children }) => (
                                          <table className="min-w-full bg-white border border-gray-300">{children}</table>
                                        ),
                                        thead: ({ children }) => (
                                          <thead className="border-gray-300">{children}</thead>
                                        ),
                                        tbody: ({ children }) => (
                                          <tbody>{children}</tbody>
                                        ),
                                        tr: ({ children }) => (
                                          <tr className="border-b border-gray-300">{children}</tr>
                                        ),
                                        th: ({ children }) => (
                                          <th className="px-4 py-2 text-left">{children}</th>
                                        ),
                                        td: ({ children }) => (
                                          <td className="px-4 py-2">{children}</td>
                                        ),
                                      }}
                                    >
                                        {currentAnswer}  
                                      </ReactMarkdown>
                                    </div>
                                </div>
                            </div>}
                    </div>
                    )
                }
              <div ref={messagesEndRef} />
            </div>
          </div>
          <div className={styles.footer}>
            <div className="w-[66%] flex flex-row justify-between items-start">
              <div>
                <img 
                  src="/altgan-logo.svg" 
                  alt="AltGAN Logo" 
                  className="w-8 h-8 rounded-xl bg-gray-900 mb-2 object-contain"
                />
              </div>
              <button
                onClick={() => {
                  const newMode = mode === 'answer' ? 'report' : 'answer';
                  setMode(newMode);
                }}
                className={`px-4 py-2 mb-2 rounded-lg transition-colors duration-200 flex flex-row items-center gap-2 ${
                  mode === 'report' 
                    ? 'bg-slate-300 text-white' 
                    : 'border-solid rounded-xl !border !border-solid border-slate-100 text-gray-700 hover:bg-slate-100'
                }`}
              >
                <DeepResearch />
                Deep Research
              </button>
            </div>
            <div className="w-full flex flex-row justify-center">
              <div className="relative flex flex-row w-[66%] items-center  gap-5 rounded-3xl">
                <div className="w-full rounded-xl relative">
                    {loading && (
                      <div className="absolute top-3 left-3 text-gray-500">
                        Generating {mode === 'report' ? 'report' : 'answer'}
                        <span className="inline-flex items-center">
                          <span className="animate-[bounce_1s_infinite_0ms]">.</span>
                          <span className="animate-[bounce_1s_infinite_100ms]">.</span>
                          <span className="animate-[bounce_1s_infinite_200ms]">.</span>
                        </span>
                      </div>
                    )}
                    <textarea
                      className={`${styles.promptInput} ${loading ? 'pt-8' : ''}`}
                      rows={3}
                      value={loading ? "" : prompt}
                      onChange={handleChange}
                      disabled={loading}
                      placeholder={loading ? "" :"Type your question here..."}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                    />
                </div>
                <div className="absolute bottom-center right-6">
                  {loading ? (
                    <button
                      type="button"
                      className="w-6 h-6 flex items-center justify-center animate-pulse cursor-pointer"
                      onClick={handleStop}
                      tabIndex={-1}
                    >
                      <StopIcon />
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="w-6 h-6 flex items-center justify-center cursor-pointer"
                      onClick={handleSend}
                      tabIndex={-1}
                    >
                      <SendIcon />
                    </button>
                  )}
                </div>
                {/* <div className={styles.stopMessage}>
                  {loading ? (
                    <div
                      className="w-4 h-4 animate-pulse cursor-pointer"
                      onClick={() => handleStop()}
                    >
                      <StopIcon />
                    </div>
                  ) : (
                    <div
                      className="w-6 h-6 cursor-pointer"
                      onClick={() => handleSend()}
                    >
                      <SendIcon />
                    </div>
                  )}
                </div> */}
              </div>
            </div>
          </div>
          {/* <div className={styles.footer}>
            <div className="w-full">
              <TextArea className="w-full"
                name="icoutlineinfo"
                placeholder={"Please select the category and the model responds accordingly"}
                value={category ? `Model will help you with anything related to ${category.label}` : ""}
              />
              <div className="relative mt-[-18px] flex items-center justify-between gap-5 rounded border border-solid border-blue_gray-900_01 bg-gray-900_04 px-2.5 py-3">
              <div className="w-full">
                    <Input input={loading ? "" : prompt}
                onKeyDown={() => handleSend()}
                handleKeyDown={handleKeyDown}
                handleChange={handleChange}
                loading={loading} value={prompt} className="spotlight_input"></Input>
                    </div>
                  <div className={styles.stopMessage}>
                    {loading ? (
                      <div
                        className="w-4 h-4 animate-pulse cursor-pointer"
                        onClick={() => handleStop()}
                      >
                        <StopIcon />
                      </div>
                    ) : (
                      <div
                        className="w-6 h-6 cursor-pointer"
                        onClick={() => handleSend()}
                      >
                        <SendIcon />
                      </div>
                    )}
                  </div>
              </div>
            </div>
          </div> */}
        </div>
       </div>
    </>
  );
}

export default App;
