import { Img, SelectBox, Heading, Button } from "./..";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MenuItem, Menu, Sidebar, sidebarClasses } from "react-pro-sidebar";
import { Chat, ChatEntry } from "../interfaces";
import styles from './sidebar.module.css';
import ConfirmationModal from "./chatMenu";
import { selectOptionType } from "../SelectBox";

const dropDownOptions = [
  { label:"Finance", value: "finance" },
  { label: "Oil and Gas", value: "oil_gas" },
];
interface Props {
  className?: string;
  chats: { [key: string]: Chat };
  handleCategoryChange: (option: selectOptionType) => void;
 //onClick: () => void;
  chatId: string;
  newChatHandler: () => void;
  handleThreadChange: (chatId: string) => void;
  renameChat: (activeChatId: string, newTitle : string) => void;
  deleteChat: (chatId: string) => void;
}

export default function Sidebar1({ ...props }: Props) {
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [chatToDelete, setChatToDelete] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState<string>("");
  const [showMenu, setShowMenu] = useState<string | null>(null);
  const [showAllChats, setShowAllChats] = useState(false);
  const [searchText, setSearchText] = useState<string>("");
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [isSignInModalOpen, setIsSignInModalOpen] = useState(false);

  

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isSearchExpanded && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isSearchExpanded]);

  useEffect(() => {
    if (editingChatId && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editingChatId]);
  
  const handleRename = (chatId: string) => {
    // const newTitle = prompt("Enter new title for the chat:");
    // if (newTitle) {
    //   props.renameChat(chatId, newTitle);
    // }
    // setShowMenu(null);
    setEditingChatId(chatId);
    setNewTitle(props.chats[chatId].title);
    closeMenu(chatId);
  };
  const handleRenameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingChatId && newTitle?.trim() !== "") {
      props.renameChat(editingChatId, newTitle? newTitle.trim() : "");
      setEditingChatId(null);
    }
  };
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showMenu && menuRef.current && event.target instanceof Node) {
        if (!menuRef.current.contains(event.target)) {
          setShowMenu(null);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu]);

  const filteredChats = useMemo(() => {
    if (!searchText.trim()) return props.chats;
    
    return Object.entries(props.chats).reduce((acc, [id, chat]) => {
      // Check if chat title or any message contains the search text
      const matchesSearch = 
        chat.title.toLowerCase().includes(searchText.toLowerCase()) ||
        chat.chatEntries.some(entry => 
          entry.user.toLowerCase().includes(searchText.toLowerCase()) ||
          entry.bot.toLowerCase().includes(searchText.toLowerCase())
        );
      
      if (matchesSearch) {
        acc[id] = chat;
      }
      return acc;
    }, {} as { [key: string]: Chat });
  }, [props.chats, searchText]);

  // Function to handle deleting a chat
  const closeMenu = (id: string) => {
    setShowMenu(null);
  };
  const handleDelete = (idToDelete: string) => {
    setChatToDelete(idToDelete);
    setIsDeleteModalOpen(true);
    closeMenu(idToDelete);
    // if (window.confirm("Are you sure you want to delete this chat?")) {
    //   props.deleteChat(idToDelete);
    // }
    // setShowMenu(null);
  };
  const confirmDelete = () => {
    if (chatToDelete) {
      props.deleteChat(chatToDelete);
      setIsDeleteModalOpen(false);
      setChatToDelete(null);
    }
  };

  return (
    <div className={`${styles.sidebarWrapper} !border-r !border-solid border-slate-300`}>
        <div
          {...props}
          className={`${styles.sidebar} flex flex-col justify-between top-0 !sticky z-50`}
        >
          <div className="self-stretch p-3 pt-2 pb-0 flex flex-row justify-between items-center">
              <div className="flex items-center gap-2 rounded-[10px] p-3 pl-2 pt-0">
                    {/* <div className="flex rounded-[5px] !bg-black-900">
                        <Img src="/images/altgan_logo.svg" alt="Apex" className="h-[36px] w-[48px] rounded-[50%]" />
                    </div> */}
                    <div className="flex items-center">
                        <span className="text-5xl font-extrabold text-black-900 relative" style={{ lineHeight: 1 }}>
                          O
                          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-2xl">
                            🐋
                          </span>
                        </span>
                        <span className="text-4xl font-extrabold text-black-900" style={{ letterSpacing: '0.05em' }}>
                          rca
                        </span>
                    </div>
                {/* <div className="flex flex-1">
                  <Heading size="textmd" as="p" className="tracking-[-0.10px] !text-white-a700_01">
                    <div className="flex items-center gap-2 text-3xl font-extrabold text-blue-900 drop-shadow">
                      <span role="img" aria-label="orca">🐋</span> Orca
                    </div>
                  </Heading>
                </div> */}
              </div>
              <div className="self-stretch flex p-3 pt-1 flex-row items-center">
                <Button
                  className="flex w-full flex-row items-center justify-start rounded bg-gradient text-left font-sfprorounded text-[14px] font-medium tracking-[-0.08px] text-black-a700_01 sm:px-5"
                  leftIcon={<Img src="/images/img_addline.svg" alt="Add-line" className="h-[30px] w-[40px]" />} onClick={props.newChatHandler}
                >
                </Button>
              </div>
          </div>
          
          {/* <div className="flex flex-col gap-4 self-stretch p-4">
            <div className="flex items-center justify-between gap-4">
              <Heading as="p" className="uppercase">
                Select Category
              </Heading>
              <Img src="/images/img_ic_outline_info.svg" alt="Icoutlineinfo" className="h-[18px] w-[18px]" />
            </div>
            <SelectBox
              indicator={<Img src="/images/img_arrowdown.svg" alt="Arrow Down" className="h-[20px] w-[20px]" />}
              name="invite_one"
              placeholder={`Select an option`}
              options={dropDownOptions}
              onChange={(option: selectOptionType) => props.handleCategoryChange(option)}
              className="flex gap-4 rounded border border-solid border-blue_gray-900_03 p-2.5 font-inter text-[14px] tracking-[-0.08px] text-gray-300 shadow-xs"
            />
          </div> */}
          <div className="px-2 pt-0">
            <div className={`relative flex h-full items-center rounded-xl !border !border-solid border-slate-100 ${
              isSearchExpanded ? 'w-full' : 'w-full'
            }`}>
              {/* Search Icon Button */}
              <button
                onClick={() => setIsSearchExpanded(!isSearchExpanded)}
                className={`relative left-0 z-10 p-2 pl-3 text-gray-400 hover:text-gray-600 transition-colors ${
                  isSearchExpanded ? 'mr-2' : ''
                }`}
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </button>

              {/* Search Input */}
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search chats..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                className={`w-full h-full px-2 pl-12 text-sm rounded-lg border border-solid border-black
                  ${isSearchExpanded ? 'opacity-100' : 'opacity-100'}`}
                onBlur={() => {
                  if (!searchText) {
                    setIsSearchExpanded(false);
                  }
                }}
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            <Menu
              menuItemStyles={{
                button: {
                  padding: "8px",
                  borderRadius: "8px"
                },
              }}
              rootStyles={{ ["&>ul"]: { gap: "4px" } }}
              className="flex w-full flex-col self-stretch pl-3 pr-5"
            >
              <MenuItem
                className="mb-4`"
                suffix={<Img src="/images/img_filter_3_fill.svg" alt="Filter3fill" className="h-[20px] w-[20px] self-end" />
                }
              >
                <p className="flex font-extrabold">Your chats</p>
              </MenuItem>
              <div className="relative mt-2">
                {Object.keys(filteredChats).map((id, index) => (
                  <div className="flex rounded-lg" key={index}>
                    <MenuItem key={index} className={`text-black-a700_01 rounded-lg ${styles.chatThread}
                    ${
                      id === props.chatId ? "bg-slate-200" : "hover:bg-slate-100"
                    }`} onClick={() => props.handleThreadChange(id)} style={{ backgroundColor: props.chatId === id ? 'rgb(203 213 225)' : ''}}>
                      <div className="flex justify-between items-center w-full">
                      {editingChatId === id ? (
                        <form onSubmit={handleRenameSubmit} className="flex-grow">
                          <input
                            ref={inputRef}
                            type="text"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            onBlur={handleRenameSubmit}
                            className="w-full bg-transparent text-white border-none outline-none"
                          />
                        </form>
                      ) : (
                        <div className="max-w-[70%] overflow-hidden text-ellipsis">{props.chats[id].title}</div>
                      )}
                          {props.chatId==id && <div className={`flex ${styles.ellipsis}`}
                                onClick={(e) => {
                                  e.stopPropagation(); // Prevent triggering the parent MenuItem's onClick
                                  setActiveChatId(id);
                                  setShowMenu( showMenu===id ? null : id);
                                }}
                          >
                            <Img src="/horizontalEllipsis.svg" alt="Arrow Down" className="h-[20px] w-[20px] items-center justify-center" />
                          </div>}
                    </div>
                    </MenuItem>
                    {showMenu==id && (
                      <div ref={menuRef} className={styles.popUp}>
                        <div className="rounded">
                          <button
                            className="block rounded w-full text-left p-2 hover:bg-gray-400 hover:text-slate-950 text-white-a700_01 "
                            onClick={() => handleRename(id)}
                          >
                            Rename
                          </button>
                          <button
                            className="block w-full text-left p-2 hover:bg-gray-400 hover:text-slate-950 text-white-a700_01"
                            onClick={() => handleDelete(id)}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                  
                ))}
              </div>
            </Menu>
          </div>
        </div>
        {/* Altgan Logo*/}
        <div>
          <div className="px-3 py-4 mt-auto">
              <button
                onClick={() => setIsSignInModalOpen(true)}
                className="w-full bg-slate-300 hover:bg-slate-400 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Sign In
              </button>
            </div>
        </div>
        <ConfirmationModal
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          onConfirm={confirmDelete}
          message="Are you sure you want to delete this chat?"
        />
    </div>
    
  );
}
