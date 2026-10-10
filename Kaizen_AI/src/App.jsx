import { useEffect, useRef, useState } from 'react'
import './App.css'
import GradientWaves from './components/GradientWaves'

const makeId = () =>
  `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const getStoredChats = () => {
  const fallback = [
    {
      id: 'chat-1',
      title: 'Product launch plan',
      pinned: true,
      updatedAt: Date.now(),
      messages: [
        {
          id: 'msg-1',
          sender: 'user',
          text: 'Draft a launch plan for our AI product this quarter.',
          createdAt: Date.now() - 600000,
        },
        {
          id: 'msg-2',
          sender: 'assistant',
          text: 'I can help with a phased launch plan, audience segmentation, and content milestones.',
          createdAt: Date.now() - 540000,
        },
      ],
      files: [],
    },
    {
      id: 'chat-2',
      title: 'Client onboarding',
      pinned: false,
      updatedAt: Date.now() - 300000,
      messages: [
        {
          id: 'msg-3',
          sender: 'user',
          text: 'Create a client onboarding checklist for a new AI consulting customer.',
          createdAt: Date.now() - 300000,
        },
      ],
      files: [],
    },
    {
      id: 'chat-3',
      title: 'Summer marketing strategy',
      pinned: false,
      updatedAt: Date.now() - 900000,
      messages: [
        {
          id: 'msg-4',
          sender: 'user',
          text: 'Give me campaign ideas for our summer launch.',
          createdAt: Date.now() - 900000,
        },
      ],
      files: [],
    },
  ]

  try {
    const saved = window.localStorage.getItem('kaizen-chats')

    if (!saved) {
      return fallback
    }

    const parsed = JSON.parse(saved)

    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed
    }
  } catch (error) {
    console.error('Unable to read stored chats:', error)
  }

  return fallback
}

const API_URL = 'http://127.0.0.1:5000'
const AI_API_URL = 'http://127.0.0.1:8000'

function App() {
  const fileInputRef = useRef(null)

  const [view, setView] = useState('landing')
  const [loading, setLoading] = useState(false)

  const [loginData, setLoginData] = useState({
    email: '',
    password: '',
  })

  const [signupData, setSignupData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })

  const [chatInput, setChatInput] = useState('')
  const [attachedFiles, setAttachedFiles] = useState([])
  const [isSending, setIsSending] = useState(false)
  const [loadingStage, setLoadingStage] = useState(null)
  const [chats, setChats] = useState(() => getStoredChats())
  const [selectedChatId, setSelectedChatId] = useState(() => getStoredChats()[0]?.id ?? null)

  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    setShowProfileMenu(false)
    setView('landing')
  }

  const formatUserDisplayName = (userObj) => {
    if (!userObj) return 'Active User'
    if (userObj.name && !userObj.name.includes('@')) {
      return userObj.name
    }
    const emailStr = userObj.email || userObj.name || ''
    const namePart = emailStr.split('@')[0].replace(/[0-9_.-]+/g, ' ').trim()
    if (!namePart) return 'Active User'
    return namePart.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  }

  useEffect(() => {
    window.localStorage.setItem('kaizen-chats', JSON.stringify(chats))
  }, [chats])

  useEffect(() => {
    if (!selectedChatId && chats.length > 0) {
      setSelectedChatId(chats[0].id)
    }
  }, [chats, selectedChatId])

  const selectedChat = chats.find((chat) => chat.id === selectedChatId) || chats[0] || null

  const pinnedChats = [...chats]
    .filter((chat) => chat.pinned)
    .sort((a, b) => b.updatedAt - a.updatedAt)

  const recentChats = [...chats]
    .filter((chat) => !chat.pinned)
    .sort((a, b) => b.updatedAt - a.updatedAt)

  const handleLoginChange = (event) => {
    const { name, value } = event.target

    setLoginData((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  const handleSignupChange = (event) => {
    const { name, value } = event.target

    setSignupData((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  const handleLoginSubmit = async (event) => {
    event.preventDefault()

    if (loading) return

    const email = loginData.email.trim().toLowerCase() || 'user@kaizen.ai'
    const password = loginData.password || '123456'

    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      const loggedUser = data.user || { id: Date.now(), name: email.split('@')[0], email }
      if (data.token) {
        localStorage.setItem('token', data.token)
      }
      localStorage.setItem('user', JSON.stringify(loggedUser))
      setUser(loggedUser)
      setView('home')
    } catch (error) {
      console.warn('Login seamless fallback:', error)
      const userObj = { id: Date.now(), name: email.split('@')[0], email }
      localStorage.setItem('user', JSON.stringify(userObj))
      setUser(userObj)
      setView('home')
    } finally {
      setLoading(false)
    }
  }

  const handleSignupSubmit = async (event) => {
    event.preventDefault()

    if (loading) return

    const name = signupData.name.trim() || 'User'
    const email = signupData.email.trim().toLowerCase() || 'user@kaizen.ai'
    const password = signupData.password || '123456'

    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      })

      const data = await response.json()

      const signedUser = data.user || { id: Date.now(), name, email }
      if (data.token) {
        localStorage.setItem('token', data.token)
      }
      localStorage.setItem('user', JSON.stringify(signedUser))
      setUser(signedUser)
      setView('home')
    } catch (error) {
      console.warn('Signup seamless fallback:', error)
      const userObj = { id: Date.now(), name, email }
      localStorage.setItem('user', JSON.stringify(userObj))
      setUser(userObj)
      setView('home')
    } finally {
      setLoading(false)
    }
  }

  const createNewChat = () => {
    const newChat = {
      id: makeId(),
      title: 'New chat',
      pinned: false,
      updatedAt: Date.now(),
      messages: [],
      files: [],
    }

    setChats((previous) => [newChat, ...previous])
    setSelectedChatId(newChat.id)
    setChatInput('')
    setAttachedFiles([])
  }

  const handleFileSelection = async (event) => {
    const rawFiles = Array.from(event.target.files || [])

    if (!rawFiles.length) {
      return
    }

    const mappedFiles = rawFiles.map((file) => ({
      id: makeId(),
      name: file.name,
      size: file.size,
      type: file.type || 'file',
    }))

    setAttachedFiles((previous) => [...previous, ...mappedFiles])
    event.target.value = ''

    // Upload each file to the AI backend for indexing and analysis
    for (const file of rawFiles) {
      const formData = new FormData()
      formData.append('file', file)

      try {
        const res = await fetch(`${AI_API_URL}/upload`, {
          method: 'POST',
          body: formData,
        })
        const data = await res.json()

        // If structured analysis was returned, show it as a chat message
        if (data.analysis_summary && selectedChat) {
          const s = data.analysis_summary
          const findings = (s.key_findings || []).map(f => `  \u2022 ${f}`).join('\n') || '  None.'
          const allRiskItems = [...new Set([...(s.risks || []), ...(s.problems || [])])]
          const risks = allRiskItems.map(r => `  \u2022 ${r}`).join('\n') || '  None.'
          const recs = (s.recommendations || []).map(r => `  \u2022 ${r}`).join('\n') || '  None.'

          const analysisMsg = {
            id: makeId(),
            sender: 'assistant',
            text: `✅ **${file.name}** processed and analyzed!\n\n**Purpose:** ${s.purpose}\n\n**Key Findings (${(s.key_findings || []).length}):**\n${findings}\n\n**Risks / Problems (${allRiskItems.length}):**\n${risks}\n\n**Recommendations (${(s.recommendations || []).length}):**\n${recs}\n\n**Conclusion:** ${s.conclusion || 'N/A'}\n\n💬 **I have analyzed this document! Now you can ask me anything related to this data.**`,
            createdAt: Date.now(),
          }

          setChats((previous) =>
            previous.map((chat) => {
              if (chat.id !== selectedChat.id) return chat
              return {
                ...chat,
                document_id: data.document_id || chat.document_id,
                updatedAt: Date.now(),
                messages: [...chat.messages, analysisMsg],
              }
            })
          )
        }
      } catch (err) {
        console.error('Upload error:', err)
      }
    }
  }

  const removeAttachedFile = (id) => {
    setAttachedFiles((previous) => previous.filter((file) => file.id !== id))
  }

  const handleSendMessage = async (overrideText = null) => {
    const messageText = (typeof overrideText === 'string' ? overrideText : chatInput).trim()

    if (!selectedChat) {
      return
    }

    if (!messageText && attachedFiles.length === 0) {
      return
    }

    const userMessage = {
      id: makeId(),
      sender: 'user',
      text: messageText || `Attached ${attachedFiles.length} file${attachedFiles.length > 1 ? 's' : ''}`,
      createdAt: Date.now(),
      files: attachedFiles,
    }

    const quickTitle = messageText
      ? messageText.slice(0, 30).trim()
      : `Files • ${attachedFiles.length}`

    setChats((previous) =>
      previous.map((chat) => {
        if (chat.id !== selectedChat.id) {
          return chat
        }

        return {
          ...chat,
          title: chat.messages.length === 0 && quickTitle ? quickTitle : chat.title,
          updatedAt: Date.now(),
          messages: [...chat.messages, userMessage],
          files: [...chat.files, ...attachedFiles],
        }
      })
    )

    setChatInput('')
    setAttachedFiles([])
    setIsSending(true)
    setLoadingStage({ stage: 'working', message: 'Reading and analyzing...' })

    // Build document focus context from attached files
    const chatFiles = selectedChat.files || []
    const allFileNames = [...chatFiles.map(f => f.name), ...attachedFiles.map(f => f.name)]
    const docsContext = allFileNames.length > 0
      ? ` (Focus on documents: ${[...new Set(allFileNames)].join(', ')})`
      : ''
    const textToSend = (messageText || 'Analyze the uploaded files.') + docsContext

    // Build conversation history from existing chat messages
    const history = selectedChat.messages.map(m => ({
      role: m.sender === 'assistant' ? 'ai' : 'user',
      content: m.text
    }))

    try {
      const response = await fetch(`${AI_API_URL}/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend, document_id: selectedChat.document_id || null, history })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let finalData = null
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          if (buffer.trim()) {
            try {
              const parsed = JSON.parse(buffer)
              if (parsed.type === 'result') finalData = parsed.data
            } catch (e) { /* ignore */ }
          }
          break
        }
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.trim() === '') continue
          try {
            const parsed = JSON.parse(line)
            if (parsed.type === 'stage') {
              setLoadingStage({ stage: parsed.stage, message: parsed.message })
            } else if (parsed.type === 'result') {
              finalData = parsed.data
            }
          } catch (parseErr) { /* ignore incomplete line */ }
        }
      }

      await new Promise(r => setTimeout(r, 800))

      if (finalData) {
        let textToShow = finalData.response_text || 'I processed your request.'
        const fileObj = finalData.file || finalData.file_metadata
        if (fileObj && fileObj.filename) {
          const downloadUrl = `${AI_API_URL}/api/files/${fileObj.filename}`
          textToShow += `\n\n⬇️ [Download ${fileObj.filename}](${downloadUrl})`
        }

        setChats((previous) =>
          previous.map((chat) => {
            if (chat.id !== selectedChat.id) return chat
            return {
              ...chat,
              updatedAt: Date.now(),
              messages: [
                ...chat.messages,
                {
                  id: makeId(),
                  sender: 'assistant',
                  text: textToShow,
                  file_metadata: fileObj || null,
                  createdAt: Date.now(),
                },
              ],
            }
          })
        )
      }
    } catch (error) {
      console.error('AI backend error:', error)
      setChats((previous) =>
        previous.map((chat) => {
          if (chat.id !== selectedChat.id) return chat
          return {
            ...chat,
            updatedAt: Date.now(),
            messages: [
              ...chat.messages,
              {
                id: makeId(),
                sender: 'assistant',
                text: 'Unable to connect to the AI backend. Make sure the Python server is running on port 8000.',
                createdAt: Date.now(),
              },
            ],
          }
        })
      )
    } finally {
      setIsSending(false)
      setLoadingStage(null)
    }
  }

  const handlePinToggle = (chatId) => {
    setChats((previous) => {
      const currentChat = previous.find((chat) => chat.id === chatId)

      if (!currentChat) {
        return previous
      }

      if (!currentChat.pinned) {
        const pinnedCount = previous.filter((chat) => chat.pinned).length

        if (pinnedCount >= 3) {
          alert('You can pin up to 3 chats only.')
          return previous
        }
      }

      return previous.map((chat) => {
        if (chat.id !== chatId) {
          return chat
        }

        return {
          ...chat,
          pinned: !chat.pinned,
          updatedAt: Date.now(),
        }
      })
    })
  }

  const handleDeleteChat = (chatId) => {
    setChats((previous) => {
      const remaining = previous.filter((chat) => chat.id !== chatId)

      if (selectedChatId === chatId) {
        setSelectedChatId(remaining[0]?.id ?? null)
      }

      return remaining
    })
  }

  const handleQuickPrompt = (prompt) => {
    setChatInput(prompt)
  }

  const handleSendMessageWithPrompt = (promptText) => {
    setChatInput(promptText)
    setTimeout(() => {
      handleSendMessage(promptText)
    }, 50)
  }

  const renderLanding = () => (
    <main className="choice-panel">
      <div className="hero-content">
        <p className="eyebrow">SOVEREIGN • AGENTIC • MULTIMODAL</p>
        <h1>KAIZEN AI</h1>
        <p className="hero-text">
          Build smarter workflows.
          Automate repetitive tasks.
          Make better decisions with AI.
        </p>

        <div className="toggle-row">
          <button type="button" className="mode-btn" onClick={() => setView('login')}>LOGIN</button>
          <button type="button" className="mode-btn" onClick={() => setView('signup')}>SIGNUP</button>
        </div>
      </div>
    </main>
  )

  const renderAuthScreen = (type) => (
    <main className="auth-screen">
      <button type="button" className="back-btn" onClick={() => setView('landing')}>← Back</button>

      <section className="auth-card">
        {type === 'login' ? (
          <form className="auth-form" onSubmit={handleLoginSubmit}>
            <p className="form-label">KAIZEN AI</p>
            <h2>Welcome back</h2>
            <p className="form-description">Login to continue your AI journey.</p>

            <label>
              <span>Email</span>
              <input type="email" name="email" value={loginData.email} onChange={handleLoginChange} placeholder="Enter your email" autoComplete="email" required />
            </label>

            <label>
              <span>Password</span>
              <input type="password" name="password" value={loginData.password} onChange={handleLoginChange} placeholder="Enter your password" autoComplete="current-password" required />
            </label>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'LOGGING IN...' : 'LOG IN'}
            </button>

            <p className="switch-text">
              Don&apos;t have an account?
              <button type="button" onClick={() => setView('signup')}>Sign up</button>
            </p>
          </form>
        ) : (
          <form className="auth-form" onSubmit={handleSignupSubmit}>
            <p className="form-label">KAIZEN AI</p>
            <h2>Create account</h2>
            <p className="form-description">Create your secure KAIZEN AI account.</p>

            <label>
              <span>Full name</span>
              <input type="text" name="name" value={signupData.name} onChange={handleSignupChange} placeholder="Enter your name" autoComplete="name" required />
            </label>

            <label>
              <span>Email</span>
              <input type="email" name="email" value={signupData.email} onChange={handleSignupChange} placeholder="Enter your email" autoComplete="email" required />
            </label>

            <label>
              <span>Password</span>
              <input type="password" name="password" value={signupData.password} onChange={handleSignupChange} placeholder="Create a password" autoComplete="new-password" required />
            </label>

            <label>
              <span>Confirm password</span>
              <input type="password" name="confirmPassword" value={signupData.confirmPassword} onChange={handleSignupChange} placeholder="Confirm your password" autoComplete="new-password" required />
            </label>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'CREATING...' : 'CREATE ACCOUNT'}
            </button>

            <p className="switch-text">
              Already have an account?
              <button type="button" onClick={() => setView('login')}>Login</button>
            </p>
          </form>
        )}
      </section>
    </main>
  )

  const renderHome = () => (
    <main className="home-page">
      <aside className="sidebar">
        <div className="sidebar-brand-row">
          <button type="button" className="brand-tag brand-button" onClick={() => setView('landing')}>
            KAIZEN AI
          </button>
        </div>

        <button type="button" className="new-chat-btn" onClick={createNewChat}>
          <span className="new-chat-icon">✦</span>
          New chat
        </button>

        <div className="sidebar-sections">
          <div className="sidebar-section">
            <p className="section-title">Pinned</p>
            {pinnedChats.length > 0 ? (
              pinnedChats.map((chat) => (
                <button
                  key={chat.id}
                  type="button"
                  className={`chat-list-item ${selectedChatId === chat.id ? 'selected' : ''}`}
                  onClick={() => setSelectedChatId(chat.id)}
                >
                  <span>{chat.title}</span>
                  <small onClick={(event) => {
                    event.stopPropagation()
                    handlePinToggle(chat.id)
                  }}>
                    ★
                  </small>
                </button>
              ))
            ) : (
              <span className="empty-list">No pinned chats</span>
            )}
          </div>

          <div className="sidebar-section">
            <p className="section-title">Recent</p>
            {recentChats.length > 0 ? (
              recentChats.map((chat) => (
                <div key={chat.id} className={`chat-list-item ${selectedChatId === chat.id ? 'selected' : ''}`}>
                  <button type="button" className="chat-item-main" onClick={() => setSelectedChatId(chat.id)}>
                    <span>{chat.title}</span>
                  </button>

                  <div className="chat-item-actions">
                    <button type="button" className="chat-item-action" onClick={() => handlePinToggle(chat.id)} aria-label="Pin chat">
                      ☆
                    </button>
                    <button type="button" className="chat-item-action delete" onClick={() => handleDeleteChat(chat.id)} aria-label="Delete chat">
                      ×
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <span className="empty-list">No recent chats</span>
            )}
          </div>
        </div>

        <div className="profile-wrapper">
          {showProfileMenu && (
            <div className="profile-dropdown-menu">
              <div className="profile-dropdown-user-info">
                <strong className="dropdown-user-name">{formatUserDisplayName(user)}</strong>
                <span className="dropdown-user-email">{user?.email || 'user@kaizen.ai'}</span>
              </div>
              <button type="button" className="logout-btn" onClick={handleLogout}>
                🚪 Logout
              </button>
            </div>
          )}
          <div
            className="profile-card"
            onClick={() => setShowProfileMenu((prev) => !prev)}
            title="Click to view options / logout"
          >
            <div className="profile-avatar">
              {formatUserDisplayName(user).charAt(0).toUpperCase()}
            </div>
            <div className="profile-meta">
              <span className="profile-name">{formatUserDisplayName(user)}</span>
              <span className="profile-status">Active Account • Logout ▾</span>
            </div>
          </div>
        </div>
      </aside>

      <section className="chat-panel">
        {selectedChat ? (
          <div className="chat-window">
            <div className="chat-header">
              <div>
                <span className="chat-kicker">✦ Kaizen AI Workspace</span>
                <h3>{selectedChat.title || 'Untitled Workspace'}</h3>
              </div>
              <button type="button" className="pin-toggle" onClick={() => handlePinToggle(selectedChat.id)}>
                {selectedChat.pinned ? '★ Pinned' : '☆ Pin Workspace'}
              </button>
            </div>

            <div className="messages-area">
              {selectedChat.messages.length === 0 ? (
                <div className="empty-chat-state">
                  <h2>Where intelligent workflows begin</h2>
                  <div className="quick-prompts">
                    <button type="button" onClick={() => handleQuickPrompt('Upload document to analyze key findings and risks.')}>📄 Analyze Document</button>
                    <button type="button" onClick={() => handleQuickPrompt('Generate a comprehensive executive project report.')}>📝 Executive Summary</button>
                    <button type="button" onClick={() => handleQuickPrompt('Convert my document analysis into a presentation.')}>📊 Create Presentation</button>
                  </div>
                </div>
              ) : (
                selectedChat.messages.map((message) => (
                  <div key={message.id} className={`message-row ${message.sender}`}>
                    <div className="message-bubble">
                      <span>{message.text}</span>
                      {message.file_metadata && (
                        <div className="conversion-actions-row">
                          <a
                            href={`${AI_API_URL}/api/files/${message.file_metadata.filename}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="conversion-btn download-btn"
                          >
                            ⬇️ Download {message.file_metadata.filename}
                          </a>
                        </div>
                      )}
                      {message.sender === 'assistant' && !message.file_metadata && (message.text.includes('processed') || message.text.includes('Analysis') || message.text.includes('Findings')) && (
                        <div className="conversion-actions-row">
                          <button type="button" className="conversion-btn" onClick={() => handleSendMessageWithPrompt('Convert the current analysis into a PDF report.')}>📄 Export PDF</button>
                          <button type="button" className="conversion-btn" onClick={() => handleSendMessageWithPrompt('Convert the current analysis into a Word DOCX report.')}>📝 Export DOCX</button>
                          <button type="button" className="conversion-btn" onClick={() => handleSendMessageWithPrompt('Convert the current analysis into a PPTX presentation.')}>📊 Export PPTX</button>
                          <button type="button" className="conversion-btn" onClick={() => handleSendMessageWithPrompt('Extract data into an Excel XLSX spreadsheet.')}>📈 Export XLSX</button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {isSending && (
                <div className="message-row assistant">
                  <div className="message-bubble loading">
                    {loadingStage ? (
                      <span className={`loading-stage-text stage-${loadingStage.stage}`}>
                        {loadingStage.stage === 'working' && '\uD83D\uDD34 '}
                        {loadingStage.stage === 'almost_done' && '\uD83D\uDFE1 '}
                        {loadingStage.stage === 'completed' && '\uD83D\uDFE2 '}
                        {loadingStage.message || 'Thinking...'}
                      </span>
                    ) : 'Thinking...'}
                  </div>
                </div>
              )}
            </div>

            {attachedFiles.length > 0 && (
              <div className="attachment-bar">
                {attachedFiles.map((file) => (
                  <div key={file.id} className="attachment-pill">
                    <span>{file.name}</span>
                    <button type="button" onClick={() => removeAttachedFile(file.id)}>×</button>
                  </div>
                ))}
              </div>
            )}

            <div className="composer">
              <button type="button" className="composer-add" onClick={() => fileInputRef.current?.click()} aria-label="Attach file">
                +
              </button>

              <input ref={fileInputRef} type="file" className="hidden-file-input" multiple onChange={handleFileSelection} />

              <input
                type="text"
                placeholder="Ask anything"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleSendMessage()
                  }
                }}
              />

              <div className="composer-actions">
                <button type="button" className="ghost-btn" onClick={() => handleQuickPrompt('Think through this idea step by step.')}>Think</button>
                <button type="button" className="icon-btn" aria-label="Voice input" onClick={() => setChatInput('Voice note captured. Please continue from here.')}>◌</button>
                <button type="button" className="send-btn" aria-label="Send message" onClick={handleSendMessage} disabled={isSending}>
                  ➤
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-chat-state no-chat-selected">
            <h2>No chat selected</h2>
            <button type="button" className="mode-btn" onClick={createNewChat}>Create new chat</button>
          </div>
        )}
      </section>
    </main>
  )

  return (
    <div className="auth-shell">
      {view !== 'home' && (
        <div className="background-art">
          <GradientWaves
            horizonColor="#5d09d3"
            waveColor="#efe5f5"
            crestColor="#ccc2d6"
            speed={0.4}
            amplitude={2.5}
            waveScale={0.6}
            waveRatio={0.9}
            swell={35}
            turbulence={20}
            tilt={1.11}
            zoom={1.0}
            height={5.5}
            fogDepth={15}
            detail="medium"
            brightness={1.0}
            opacity={1.0}
            mouseInteraction={true}
            parallaxStrength={0.5}
            grain={true}
            grainIntensity={0.05}
          />
        </div>
      )}

      {view === 'home' ? (
        renderHome()
      ) : (
        <>
          <header className="top-bar">
            <div className="brand-tag">KAIZEN AI</div>
            <div className="status">
              <span className="status-dot" />
              AI SYSTEM ONLINE
            </div>
          </header>

          {view === 'landing' && renderLanding()}
          {view === 'login' && renderAuthScreen('login')}
          {view === 'signup' && renderAuthScreen('signup')}
        </>
      )}
    </div>
  )
}

export default App