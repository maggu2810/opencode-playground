import { mkdir, readFile, writeFile } from "fs/promises"
import { homedir } from "os"
import path from "path"

/**
 * State manager with file locking to prevent concurrent write collisions
 */
export class StateManager {
  private stateDir: string
  private locks = new Map<string, Promise<void>>()
  
  constructor() {
    this.stateDir = path.join(homedir(), ".local", "state", "oclitellmac")
  }
  
  /**
   * Ensure state directories exist
   */
  async ensureDirectories(): Promise<void> {
    await mkdir(path.join(this.stateDir, "providers"), { recursive: true })
    await mkdir(path.join(this.stateDir, "key-info"), { recursive: true })
  }
  
  /**
   * Acquire a lock for a specific file path to prevent concurrent writes
   */
  private async withLock<T>(lockKey: string, fn: () => Promise<T>): Promise<T> {
    // Wait for any existing operation on this key
    while (this.locks.has(lockKey)) {
      await this.locks.get(lockKey)
    }
    
    // Create new lock
    let resolveLock: () => void
    const lockPromise = new Promise<void>((resolve) => {
      resolveLock = resolve
    })
    this.locks.set(lockKey, lockPromise)
    
    try {
      return await fn()
    } finally {
      // Release lock
      this.locks.delete(lockKey)
      resolveLock!()
    }
  }
  
  /**
   * Save provider cache with atomic write
   */
  async saveProviderCache(providerKey: string, data: any): Promise<void> {
    return this.withLock(`provider:${providerKey}`, async () => {
      const filePath = path.join(this.stateDir, "providers", `${providerKey}.json`)
      const content = JSON.stringify(data, null, 2)
      await writeFile(filePath, content, "utf-8")
    })
  }
  
  /**
   * Load provider cache
   */
  async loadProviderCache(providerKey: string): Promise<any | null> {
    const filePath = path.join(this.stateDir, "providers", `${providerKey}.json`)
    try {
      const content = await readFile(filePath, "utf-8")
      return JSON.parse(content)
    } catch {
      return null
    }
  }
  
  /**
   * Save budget data with atomic write and collision prevention
   */
  async saveBudgetData(providerKey: string, data: any): Promise<void> {
    return this.withLock(`budget:${providerKey}`, async () => {
      const filePath = path.join(this.stateDir, "key-info", `${providerKey}.json`)
      const content = JSON.stringify(data, null, 2)
      await writeFile(filePath, content, "utf-8")
    })
  }
  
  /**
   * Load budget data
   */
  async loadBudgetData(providerKey: string): Promise<any | null> {
    const filePath = path.join(this.stateDir, "key-info", `${providerKey}.json`)
    try {
      const content = await readFile(filePath, "utf-8")
      return JSON.parse(content)
    } catch {
      return null
    }
  }
  
  /**
   * Get state directory path
   */
  getStateDir(): string {
    return this.stateDir
  }
}
