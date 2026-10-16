import { useRef, useState, type DragEvent, type FormEvent } from "react";
import "./letter.css";

// Fill these in before the page goes live.
const X_URL = "#";
const YOUTUBE_URL = "#";
const CALL_URL = "#";

export function Letter() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const [held, setHeld] = useState(false);

  function remember(file: File | undefined) {
    const input = fileInput.current;
    if (input) {
      if (file) {
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
      } else {
        input.value = "";
      }
    }
    setFileName(file ? file.name : "");
  }

  function hold(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setHeld(true);
  }

  function drop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    remember(event.dataTransfer.files[0]);
  }

  function allow(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
  }

  return (
    <main>
      <p className="me">
        <img src="/alex.jpg" alt="Alex Havryleshko" width="64" height="64" />
        <span>
          Alex Havryleshko
          <br />
          <a href={X_URL}>X</a> · <a href={YOUTUBE_URL}>YouTube</a>
        </span>
      </p>
      <p>
        If you run a dental practice, send me one of your bills. Card fees, lab,
        supplies, energy, a service contract, anything. If you're paying too
        much I'll deal with the supplier for you.
      </p>
      <p>
        It's free and it stays free. I'm doing this in public, so I post what I
        find on X and YouTube. I never post your name or anything that shows
        which practice it is.
      </p>
      <p>I use AI to read the bills faster. I check every one myself.</p>
      <form onSubmit={hold}>
        <p>
          <label className="drop" onDragEnter={allow} onDragOver={allow} onDrop={drop}>
            {fileName || "Drop a bill here, or choose a file."}
            <input
              ref={fileInput}
              name="bill"
              type="file"
              accept="application/pdf,.pdf,image/*"
              required
              onChange={(event) => remember(event.target.files?.[0])}
            />
          </label>
        </p>
        <p>
          <label>
            Your email
            <input name="email" type="email" autoComplete="email" required />
          </label>
        </p>
        <p>
          <button type="submit">Send</button>
        </p>
        {held ? <p>This form isn't connected yet. Nothing was sent.</p> : null}
      </form>
      <p className="small">
        I'll email you back with what I found. Nothing changes with your
        suppliers until you say yes. I delete the file when we're done. If you'd
        rather talk first, <a href={CALL_URL}>book 15 minutes</a>.
      </p>
    </main>
  );
}
