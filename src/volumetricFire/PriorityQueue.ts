interface PriorityQueueItem {
  object: any;
  priority: number;
}

export class PriorityQueue {
  private contents: PriorityQueueItem[] = [];
  private sorted = false;

  sort(): void {
    this.contents.sort((a, b) => a.priority - b.priority);
    this.sorted = true;
  }

  pop(): PriorityQueueItem {
    if (!this.sorted) {
      this.sort();
    }
    return this.contents.pop()!;
  }

  top(): PriorityQueueItem {
    if (!this.sorted) {
      this.sort();
    }
    return this.contents[this.contents.length - 1];
  }

  push(object: any, priority: number): void {
    this.contents.push({ object, priority });
    this.sorted = false;
  }
}
