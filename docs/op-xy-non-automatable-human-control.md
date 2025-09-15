# OP‑XY Tasks requiring a human in the loop

The OP‑XY exposes a core set of parameters via MIDI CC (track volume, pan, FX sends, filter cutoff/resonance, LFO shape and four generic **Param 1–4** per track). A Python sequencer can therefore automate most real‑time performance parameters. However, many **system‑level** and **preset‑level** functions are not mapped to MIDI and must be set on the hardware. This document walks a coding assistant through each non‑automatable function: why it matters musically, what can still be automated, and precise instructions the agent can relay to a human operator to perform on the OP‑XY. Button names (e.g., **instrument**, **sample**, **mix**, **auxiliary**), module buttons (**M1**–**M4**) and encoder colours (dark grey, mid grey, light grey, white) match those on the device.

## 1 Engine and sample management

### 1.1 Change synth/sampler engine and load presets

* **Musical importance:** Each track hosts either a synth engine (keys, bass, wavetable), a drum sampler or a melodic sampler. Choosing the engine and preset defines the fundamental sound of the track. MIDI offers no CC for selecting the engine or browsing presets; only the loaded engine’s **Param 1–4** are addressable.

* **What can be automated:** After a preset is loaded, the four **Param** CCs can modulate its parameters, and CCs exist for track volume/pan/FX sends. The engine and preset selection itself must be done manually.

* **Human‑in‑the‑loop steps:**

* **Enter instrument mode:** Press the **instrument** button. The eight track keys light up.

* **Select a track:** Press a track key (1–8) to choose which track to modify.

* **Open the engine selector:** Hold **shift** and press **M1**. This opens the engine list[\[1\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20a%20track%20by%20pressing,track%2C%20press%20shift%20and%20M1). Use the encoders to scroll between **synth**, **drum sampler** and **sampler** engines. Press an encoder to select.

* **Browse and load presets:** To choose a preset within the current engine, hold **shift** and press the **track key** you want to change[\[1\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20a%20track%20by%20pressing,track%2C%20press%20shift%20and%20M1). The preset browser opens. Rotate the **dark‑grey** knob to toggle between **category** and **engine** views and to select a category/engine[\[2\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=category%2Fengine). Use the **mid**, **light** and **white** knobs to scroll through presets within the chosen category[\[3\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20dark%20gray%20knob,you%20wish%20to%20choose%20from). Push any encoder to load the selected preset[\[4\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20mid%20gray%2C%20light,the%20preset%20within%20that%20category).

* **Manage presets:** To scramble a sound (randomize parameters), hold the track key and press **M1**[\[5\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=if%20you%20want%20to%20mess,M1%20to%20scramble%20that%20track). To copy the current preset, hold the track key and press **M2**; to paste onto another track, hold the destination track key and press **M3**[\[6\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20copy%20a%20sound%20from,press%20M2%20to%20copy%20it). To save a preset, hold the track key and press **M4**[\[7\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=). To rename or delete a user preset, enter the preset browser, select the user preset and press **M3** to rename or **M4** to delete; edit characters with the encoders[\[8\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=).

### 1.2 Record samples and load external audio

* **Musical importance:** Sampling makes the OP‑XY a unique recorder and resampler. Capturing original sounds via the built‑in microphone, line input or USB adds personal textures. None of the actions to arm recording, choose inputs or set thresholds are exposed to MIDI.

* **What can be automated:** Once a sample is recorded, its **Param 1–4** can modulate start point, loop points, tuning and other parameters if assigned. Playback of recorded samples can be automated by sending MIDI notes. The recording process itself must be manual.

* **Human‑in‑the‑loop steps:**

* **Enter sample mode:** Press **sample** to open the sampling screen.

* **Select the input:** Rotate the **dark‑grey** knob to choose the input source (e.g., mic, line, USB). Hold **shift** and rotate the same knob to select the input channel[\[9\]](https://teenage.engineering/guides/op-xy/sample#:~:text=).

* **Set gain and threshold:** Rotate the **light‑grey** knob to adjust recording gain; rotate the **white** knob to set the recording threshold (the level at which recording starts)[\[10\]](https://teenage.engineering/guides/op-xy/sample#:~:text=rotate%20the%20light%20grey%20knob,level%20on%20the%20vu%20meter).

* **Arm recording:** Hold the **record** button (**M1**) to prepare recording and press **M2** to monitor or **M4** to delete a take[\[9\]](https://teenage.engineering/guides/op-xy/sample#:~:text=).

* **Start sampling:** Press a key on the musical keyboard to start recording; the key defines the root note of the sample[\[11\]](https://teenage.engineering/guides/op-xy/sample#:~:text=start%20sampling). Release **record** to stop. You can then exit sample mode or proceed to edit the recorded sample.

### 1.3 Assign samples to pads in the drum sampler or multisampler

* **Musical importance:** Building custom drum kits or multisamples requires mapping specific samples to each pad/zone and fine‑tuning their playback. These assignments are not available via MIDI CC.

* **What can be automated:** After a sample is assigned, you can automate playback via MIDI notes and modulate parameters using **Param 1–4**. Muting or soloing can be simulated by adjusting track volume. The assignment of samples and editing of sample playback properties must be manual.

* **Human‑in‑the‑loop steps (drum sampler):**

* **Select the drum track:** In instrument mode, choose a track with the drum sampler engine. Ensure you are viewing the sampler page (press **M1** if necessary).

* **Choose a pad:** Press a key on the OP‑XY keyboard to select the drum pad; the key lights up[\[12\]](https://teenage.engineering/guides/op-xy/sample#:~:text=key%20select).

* **Record or assign a sample:** Hold **M1** to record a sample to that pad[\[13\]](https://teenage.engineering/guides/op-xy/sample#:~:text=record%20sample). To import a sample from memory, scroll through the sample browser using the encoders (hold shift to switch views) and press an encoder to assign. To monitor previous or next pad, press **M2** and **M3** respectively[\[14\]](https://teenage.engineering/guides/op-xy/sample#:~:text=previous%20sample). To clear a pad, press **M4**[\[15\]](https://teenage.engineering/guides/op-xy/sample#:~:text=clear).

* **Edit playback parameters:** On the selected pad, rotate the **dark‑grey** knob to adjust tuning[\[16\]](https://teenage.engineering/guides/op-xy/sample#:~:text=rotate%20the%20dark%20grey%20knob,the%20selected%20key%20and%20sample), the **mid‑grey** knob to set the sample start point[\[17\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20start), and the **light‑grey** knob to set the sample end[\[18\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20end). Rotate the **white** knob to choose play mode (key, oneshot, mute group or loop)[\[19\]](https://teenage.engineering/guides/op-xy/sample#:~:text=play%20mode). Hold **shift** and rotate the dark‑grey knob to flip the sample direction (forward/backward)[\[20\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20direction); shift + mid‑grey adjusts tuning again; shift + light‑grey sets cross‑fade amount[\[21\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20fade); shift + white adjusts the sample gain[\[22\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20gain). Holding **shift** and clicking the **light‑grey** knob cycles through loop types (off, forward, ping‑pong)[\[23\]](https://teenage.engineering/guides/op-xy/sample#:~:text=hold%20shift%20and%20click%20the,until%20release%20and%20loop%20off).

* **Human‑in‑the‑loop steps (multisampler):**

* **Select the multisampler track:** Choose a sampler engine track in instrument mode and press **M1** to open the sample editor.

* **Define zones:** Press a key to define the zone’s root note; hold **M1** to record audio for that zone[\[24\]](https://teenage.engineering/guides/op-xy/sample#:~:text=press%20a%20key%20to%20select,by%20pitching%20those%20samples%20down). Use **M2/M3** to navigate between zones and **M4** to clear a zone.

* **Edit start/end points and loop:** Rotate the encoders as described above to set sample start, loop start, loop end and sample end points[\[25\]](https://teenage.engineering/guides/op-xy/sample#:~:text=,152). Use shift + encoders to set direction, cross‑fade and gain.

## 2 Play behaviour and keyboard settings

### 2.1 Set play mode and portamento

* **Musical importance:** Switching between **poly**, **mono** and **legato** changes voice allocation and articulations (e.g., staccato vs. smooth). Portamento controls how notes glide between pitches. These fundamental behaviours are not accessible via CC.

* **What can be automated:** The sequencer can send note events and adjust filter or envelope via CC. It cannot switch voice modes or portamento time; these must be set manually per preset.

* **Human‑in‑the‑loop steps:**

* **Open envelopes:** Press **M2** in instrument mode to access the envelopes (amp and filter). Click an encoder to toggle between amplitude and filter envelopes[\[26\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=click%20on%20an%20encoder%20to,drum%20and%20synth%20type%20tracks).

* **Enter play‑mode menu:** Hold **shift** while remaining on **M2**; this brings up the play‑mode options[\[27\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=hold%20shift%20while%20in%20M2,to%20modify%20the%20play%20mode).

* **Select voice behaviour:** Rotate the **dark‑grey** knob to choose between **poly**, **mono** and **legato**[\[28\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20dark%20gray%20knob,play%20at%20the%20same%20time).

* **Adjust portamento:** Rotate the **mid‑grey** knob to set the portamento (glide) time between notes[\[29\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=portamento).

### 2.2 Adjust pitch‑bend range and preset volume

* **Musical importance:** The pitch‑bend range defines how far notes bend (e.g., ±2 semitones vs. ±1 octave). Preset volume balances a sound relative to other tracks. These options are not CC‑addressable.

* **What can be automated:** Software can still send pitch‑bend messages but cannot change the range; it can adjust track volume but not the preset’s inherent volume.

* **Human‑in‑the‑loop steps:** In the play‑mode menu (shift + **M2**):

* **Set bend range:** Rotate the **light‑grey** knob to choose the desired pitch‑bend range[\[30\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=bend%20range).

* **Set preset volume:** Rotate the **white** knob to adjust the preset volume; this is distinct from track volume and ensures consistent loudness[\[31\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=preset%20volume).

### 2.3 Assign pitch‑bend to other parameters or disable pitch modulation

* **Musical importance:** Reassigning the pitch‑bend strip to control a filter cutoff or other parameter allows expressive modulation beyond pitch. Disabling pitch modulation is necessary when the strip is used exclusively for modulation. These assignments are hidden in preset settings and cannot be automated via MIDI.

* **What can be automated:** Once set, the pitch‑bend strip can send modulation data. The assignment itself must be done manually.

* **Human‑in‑the‑loop steps:**

* **Open preset settings:** In instrument mode, hold **shift** and press **instrument**[\[32\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=pitchbend%20as%20a%20modulation).

* **Select the mod tab:** Rotate the **dark‑grey** knob to highlight **mod**[\[33\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=settings%2Fmod).

* **Choose “pitch‑bend target”:** Rotate the **mid‑grey** knob until “pitch‑bend” is displayed. Rotate the **light‑grey** knob to select the destination parameter (e.g., filter cutoff, LFO amount) and the **white** knob to set the modulation amount[\[34\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=pitchbend%20as%20a%20modulation).

* **Disable pitch modulation (optional):** Exit to the envelope page (**M2**). Hold **shift** and rotate the **light‑grey** knob fully counter‑clockwise; this turns off pitch‑bend’s default pitch modulation[\[35\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=now%20hold%20shift%20and%20rotate,pitchbend%E2%80%99s%20pitch%20modulation%20to%20off).

### 2.4 Enable velocity and choose velocity curve

* **Musical importance:** Velocity adds dynamic expression to MIDI notes. The OP‑XY can ignore velocity (fixed level) or respond with soft or hard curves. Changing the velocity curve is done in system settings rather than per track.

* **What can be automated:** Software can send velocity values with each note, but enabling velocity response on the device must be done manually.

* **Human‑in‑the‑loop steps:**

* **Open system settings:** Press **com** to enter communication settings. Press **M1** to open system settings.

* **Navigate to keyboard settings:** Rotate the **dark‑grey** encoder to highlight **keyboard**[\[36\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=ensure%20that%20the%20velocity%20setting,for%20more%20vigorous%20playing).

* **Select velocity response:** Rotate the **light‑grey** encoder to choose between **off**, **soft** or **hard** velocity curves[\[36\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=ensure%20that%20the%20velocity%20setting,for%20more%20vigorous%20playing). Exit **com** to apply.

## 3 Filter and LFO configuration

### 3.1 Choose the filter type

* **Musical importance:** Different filter types (ladder, state‑variable, z‑hippus, etc.) impart distinct tonal colours. The OP‑XY only exposes filter cutoff and resonance as CC parameters; selecting the filter model requires the hardware.

* **What can be automated:** After a filter type is chosen, you can automate cutoff and resonance via CC and envelope modulation.

* **Human‑in‑the‑loop steps:**

* **Enter the filter module:** Press **M3** in instrument mode.

* **Change the filter type:** Hold **shift** and press **M3**. Each press cycles through available filter models[\[37\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=M3%20is%20where%20you%20can,unique%20sound%20on%20your%20instrument). Observe the screen to see which filter is selected.

* **Exit:** Release **shift** and continue editing other parameters.

### 3.2 Select LFO type and assign destination/source

* **Musical importance:** The OP‑XY features four LFO engines (element, random, tremolo, value), each with unique behaviour. Selecting the engine and assigning its destination (e.g., filter, pitch, amplitude) and parameter is not available via CC.

* **What can be automated:** Once an LFO is configured, the **Param 1–4** CCs can modulate its shape, rate and amount (where available). The choice of engine, source and destination must be set manually.

* **Human‑in‑the‑loop steps:**

* **Enter LFO module:** Press **M4** in instrument mode.

* **Choose LFO type:** Hold **shift** and press **M4**; each press cycles through **element**, **random**, **tremolo** and **value** LFOs[\[38\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=press%20shift%20and%20M4%20in,element%2C%20random%2C%20tremolo%20and%20value).

* **Set rate/source:** Rotate the **dark‑grey** knob. For **element** LFOs, this chooses the sensor source (gyroscope, microphone, amp envelope or sum)[\[39\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=element%20uses%20the%20built,use%20as%20a%20modulation%20source). For other LFOs it adjusts the rate.

* **Set amount:** Rotate the **mid‑grey** knob to adjust how strongly the LFO affects its destination[\[40\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotating%20the%20mid%20gray%20knob,lfo%20affects%20the%20destination%20parameter).

* **Choose destination:** Rotate the **light‑grey** knob to select which module the LFO modulates (e.g., filter, pitch, volume)[\[41\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotating%20the%20light%20gray%20knob,to%20assign%20the%20lfo%20to).

* **Select parameter:** Rotate or press the **white** knob to choose the specific parameter within the destination (e.g., cutoff vs. resonance)[\[42\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotating%20or%20pressing%20down%20the,that%20you%20wish%20to%20modulate). For sub‑functions, hold **shift** and rotate encoders to access additional options[\[43\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=some%20lfos%20feature%20sub%20functions%E2%80%94you,shift%20and%20rotating%20the%20encoders).

## 4 Effects selection

### 4.1 Choose the effect on FX I and FX II

* **Musical importance:** The OP‑XY offers multiple send effects (chorus, delay, distortion, lofi, phaser). The loaded effect shapes the ambience and character of the mix. Selecting which effect is active is not CC‑controllable, although the effect’s parameters can be automated.

* **What can be automated:** After an effect is loaded, **Param 1–4** can control its parameters (rate, depth, feedback, dry/wet, etc.) via CC messages. Loading or changing the effect type must be done manually.

* **Human‑in‑the‑loop steps:**

* **Enter auxiliary mode:** Press **auxiliary**.

* **Select FX track:** Press the track key labelled **FX I** or **FX II**.

* **Open effect selector:** Hold **shift** and press **FX I** (or **FX II**). Rotate the **white** encoder to scroll through effect names[\[44\]](https://teenage.engineering/guides/op-xy/fx#:~:text=change%20fx).

* **Load effect:** Press **M1** or click the encoder to confirm selection[\[45\]](https://teenage.engineering/guides/op-xy/fx#:~:text=you%20can%20then%20use%20the,M1%20to%20confirm%20your%20selection).

* **Adjust effect parameters:** After loading, the four encoders (dark, mid, light, white) control the effect’s parameters. These can be automated via **Param 1–4** CCs.

## 5 Mix and master controls

### 5.1 Adjust the master EQ

* **Musical importance:** A global EQ shapes the tonal balance of the entire track. While individual track EQ and filter parameters can be automated, the master EQ must be set manually.

* **What can be automated:** Track volumes, pans and sends can be automated via CC, but the master EQ (low/mid/high/blend) is manual only.

* **Human‑in‑the‑loop steps:**

* **Enter mix mode:** Press **mix**.

* **Open master EQ:** Press **M2**[\[46\]](https://teenage.engineering/guides/op-xy/mix#:~:text=17).

* **Adjust bands:** Rotate the **dark‑grey**, **mid‑grey** and **light‑grey** knobs to cut or boost low, mid and high frequencies respectively[\[47\]](https://teenage.engineering/guides/op-xy/mix#:~:text=rotate%20the%20dark%20gray%20encoder,bass%20that%20is%20too%20loud).

* **Blend EQ:** Rotate the **white** knob to blend between two EQ settings, effectively controlling how strongly the EQ is applied[\[48\]](https://teenage.engineering/guides/op-xy/mix#:~:text=blend).

### 5.2 Set master saturator parameters

* **Musical importance:** The saturator adds warmth, grit and harmonic content to the mix. Four controls—gain, clip, tone and mix—shape its behaviour. No CC messages can control these, so the saturator must be adjusted manually.

* **Human‑in‑the‑loop steps:**

* **Enter mix mode:** Press **mix**.

* **Open the saturator:** Press **M3**[\[49\]](https://teenage.engineering/guides/op-xy/mix#:~:text=17).

* **Set gain:** Rotate the **dark‑grey** knob to control input gain[\[50\]](https://teenage.engineering/guides/op-xy/mix#:~:text=press%20M3%20to%20adjust%20the,master%20saturator).

* **Set clip threshold:** Rotate the **mid‑grey** knob to change how aggressively signals are clipped[\[51\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,59).

* **Adjust tone:** Rotate the **light‑grey** knob to tilt the frequency response (brighter or darker)[\[52\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,62).

* **Blend mix:** Rotate the **white** knob to set the dry/wet mix of the saturation[\[53\]](https://teenage.engineering/guides/op-xy/mix#:~:text=blend).

### 5.3 Control group levels, compression and master level

* **Musical importance:** Balancing percussion and melodic groups, adding compression and setting the final level determine the dynamics and loudness of a project. None of these controls are CC‑mapped.

* **Human‑in‑the‑loop steps:**

* **Enter mix mode:** Press **mix**.

* **Open master section:** Press **M4**[\[54\]](https://teenage.engineering/guides/op-xy/mix#:~:text=17).

* **Set percussion group level:** Rotate the **dark‑grey** knob[\[55\]](https://teenage.engineering/guides/op-xy/mix#:~:text=rotate%20the%20dark%20gray%20encoder,route%20through%20the%20percussion%20group).

* **Set melodic group level:** Rotate the **mid‑grey** knob[\[56\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,74).

* **Add compression:** Rotate the **light‑grey** knob to increase the amount of master bus compression[\[57\]](https://teenage.engineering/guides/op-xy/mix#:~:text=rotate%20the%20light%20gray%20encoder,and%20build%20a%20heavier%2C%20hard).

* **Set master level:** Rotate the **white** knob to adjust the final output level[\[58\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,80).

## 6 Auxiliary tracks and global configuration

### 6.1 Trigger punch‑in FX

* **Musical importance:** Punch‑in FX provide momentary effects like stutters, filters and glitches for live performance. They’re engaged via key presses and gyroscope movement. There is no CC to trigger them.

* **What can be automated:** Track volumes/pans can simulate some muting or gating, but the real punch‑in FX require manual intervention.

* **Human‑in‑the‑loop steps:**

* **Enter auxiliary mode:** Press **auxiliary**.

* **Select the punch‑in track:** Press the track key labelled **punch‑in** (usually track 2)[\[59\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=punch%E2%80%93in%20fx%20track).

* **Trigger FX for percussion:** Hold **shift** and press keys in the lower octave; the chosen FX applies to percussion tracks[\[60\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=some%20punch%E2%80%93in%20fx%20will%20also,while%20using%20the%20punch%E2%80%93in%20fx).

* **Trigger FX for melodic tracks:** Hold **shift** and press keys in the higher octave; the FX applies to melodic tracks[\[60\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=some%20punch%E2%80%93in%20fx%20will%20also,while%20using%20the%20punch%E2%80%93in%20fx).

* **Use gyroscope/pitch‑bend:** Some punch‑in FX respond to device movement or pitch‑bend; move the device or slide the pitch‑bend strip while holding the keys[\[61\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=some%20punch%E2%80%93in%20fx%20will%20also,while%20using%20the%20punch%E2%80%93in%20fx).

### 6.2 Configure external audio routing and multi‑out / Bluetooth

* **Musical importance:** The external audio track allows you to process live inputs through FX; the multi‑out port can send MIDI, CV/gate or audio; Bluetooth enables wireless MIDI. These are system‑level settings not accessible via CC.

* **Human‑in‑the‑loop steps:**

* **Set external audio input:** In auxiliary mode, select the **external audio** track. Rotate the **dark‑grey** knob to choose the input source (mic, line, USB) and click the knob to activate[\[62\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=OP%E2%80%93XY%20supports%20multi,with%20the%20mid%20gray%20knob). Adjust gain and FX sends using the other encoders.

* **Choose multi‑out mode:** Press **com** to open the communications screen. Rotate the **light‑grey** knob until the multi‑out port displays **MIDI** or **CV/gate**[\[63\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=start%20by%20setting%20the%20multi,is%20shown%20on%20the%20screen).

* **Advertise Bluetooth MIDI:** While in the **com** screen, press down the **dark‑grey** encoder to advertise the OP‑XY as a Bluetooth MIDI device[\[64\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=to%20connect%20the%20OP%E2%80%93XY%20to,capable%20device%20firstly%20press%20com). Pair the OP‑XY on the host computer to establish a wireless connection.

## 7 Preset settings and tuning

The preset settings menu (accessed via **shift + instrument**) includes advanced options for each sound. None of these options are exposed via MIDI, so they require manual setup before automation.

### 7.1 Apply high‑pass filter, adjust velocity sensitivity, portamento style and width

* **Musical importance:** These settings shape the timbre and playing response of a sound. A high‑pass filter removes unwanted low frequencies; velocity sensitivity determines how strongly velocity affects amplitude; portamento style changes whether glides are linear or exponential; width spreads the stereo image. Because these are preset‑level options, they aren’t adjustable via CC.

* **What can be automated:** After setting them, you can automate note events, filter sweeps and other parameters. Changing these settings mid‑performance requires physical access.

* **Human‑in‑the‑loop steps:**

* **Enter preset settings:** In instrument mode, hold **shift** and press **instrument**[\[65\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=hold%20shift%20then%20press%20instrument,to%20enter%20the%20preset%20settings).

* **Select the** settings **tab:** Rotate the **dark‑grey** knob to switch between **mod** and **settings**[\[66\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=settings%2Fmod).

* **Pick a parameter:** Rotate the **mid‑grey** knob to highlight **high‑pass**, **velocity sensitivity**, **portamento style** or **width**[\[67\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=setting).

* **Adjust the value:** Use the **light‑grey** or **white** knob to set the amount or style for the selected parameter[\[68\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20light%20gray%20or,value%20on%20the%20selected%20setting).

* **Exit:** Press any module button (M1–M4) or **instrument** to return to the main screen[\[69\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=14).

### 7.2 Remap modwheel, aftertouch, pitch‑bend and velocity

* **Musical importance:** Remapping these controllers allows you to target any synth parameter (e.g., controlling filter cutoff with modwheel). Assigning aftertouch or velocity to a new parameter can change the expressiveness of a patch. The routing must be set within each preset.

* **What can be automated:** After mapping, the controllers send their MIDI data normally. The remapping itself must be configured on the device.

* **Human‑in‑the‑loop steps:**

* **Open preset settings:** Hold **shift** \+ **instrument**.

* **Choose** mod **tab:** Rotate the **dark‑grey** knob until the **mod** tab is highlighted[\[33\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=settings%2Fmod).

* **Select the controller:** Rotate the **mid‑grey** knob to choose **modwheel**, **aftertouch**, **pitch‑bend** or **velocity**[\[70\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=setting).

* **Assign destination and amount:** Rotate the **light‑grey** knob to select the parameter you want the controller to modulate and the **white** knob to set modulation amount[\[71\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20light%20gray%20or,value%20on%20the%20selected%20setting).

* **Exit:** Press a module button or **instrument** to leave.

### 7.3 Create custom tunings and micro‑tonal scales

* **Musical importance:** Custom tunings allow micro‑tonal music and alternative scales. These are stored in user slots. MIDI cannot define tuning tables on the OP‑XY, so they need manual configuration.

* **Human‑in‑the‑loop steps:**

* **Enter preset settings:** Hold **shift** \+ **instrument**.

* **Navigate to tuning:** Select the **settings** tab with the **dark‑grey** knob and highlight **tuning** with the **mid‑grey** knob[\[72\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20create%20your%20own%20tuning%2C,go%20to%20settings%2C%20then%20tuning).

* **Select user slot:** Rotate the **light‑grey** knob to choose one of the 11 user tuning slots[\[73\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20tuning).

* **Edit tuning:** Press **M4** to edit the selected slot[\[74\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=edit). Play a note on the OP‑XY keyboard to select it, then rotate the **dark‑grey** knob to adjust its tuning in cents and the **mid‑grey** knob to adjust in micro‑cents[\[75\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20the%20note%20you%20wish,cents). Repeat for each note in the scale.

* **Exit:** Press **M1** to return to the tuning list.

### 7.4 Manage presets (view, scramble, copy, paste, save, rename, delete)

* **Musical importance:** Organising presets helps build a library of sounds for different projects. These actions are not CC‑controllable.

* **Human‑in‑the‑loop steps:**

* **View and select a preset:** In instrument mode, hold **shift** and press the track key to open the preset list[\[76\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=press%20shift%20and%20any%20track,the%20preset%20on%20that%20track). Use the **dark‑grey** knob to toggle between **category** and **engine** views[\[2\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=category%2Fengine) and to select a category or engine. Use the other knobs to pick a preset[\[3\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20dark%20gray%20knob,you%20wish%20to%20choose%20from). Click any encoder to load it[\[4\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20mid%20gray%2C%20light,the%20preset%20within%20that%20category).

* **Scramble:** Hold the track key and press **M1** to randomize the preset parameters[\[5\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=if%20you%20want%20to%20mess,M1%20to%20scramble%20that%20track).

* **Copy:** Hold the track key and press **M2**[\[77\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20copy%20a%20sound%20from,press%20M2%20to%20copy%20it).

* **Paste:** Hold the destination track key and press **M3**[\[78\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20paste%20a%20sound%20from,paste%20it%20into%20that%20track).

* **Save:** Hold the track key and press **M4** to store the current sound to a user slot[\[7\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=).

* **Rename:** In the preset list, select a user preset and press **M3**. Rotate the **dark‑grey** knob to choose characters and use other knobs to edit; confirm with **M1**[\[79\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=).

* **Delete:** Select the preset and press **M4**[\[80\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=delete%20preset).

## Conclusion

The OP‑XY’s MIDI implementation covers many performance parameters but omits crucial configuration and sound‑design tasks. The functions detailed above—engine and preset selection, sampling, sample assignment, play‑mode and pitch‑bend settings, velocity curves, filter and LFO selection, effect choice, global mix settings, punch‑in FX, external routing, preset settings, custom tunings and preset management—must be carried out on the device using buttons and encoders. A coding assistant can handle all CC‑mapped automation and sequencing while guiding the user to perform these manual steps before or during a session.

---

[\[1\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20a%20track%20by%20pressing,track%2C%20press%20shift%20and%20M1) [\[2\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=category%2Fengine) [\[3\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20dark%20gray%20knob,you%20wish%20to%20choose%20from) [\[4\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20mid%20gray%2C%20light,the%20preset%20within%20that%20category) [\[5\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=if%20you%20want%20to%20mess,M1%20to%20scramble%20that%20track) [\[6\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20copy%20a%20sound%20from,press%20M2%20to%20copy%20it) [\[7\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=) [\[8\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=) [\[26\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=click%20on%20an%20encoder%20to,drum%20and%20synth%20type%20tracks) [\[27\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=hold%20shift%20while%20in%20M2,to%20modify%20the%20play%20mode) [\[28\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20dark%20gray%20knob,play%20at%20the%20same%20time) [\[29\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=portamento) [\[30\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=bend%20range) [\[31\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=preset%20volume) [\[33\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=settings%2Fmod) [\[37\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=M3%20is%20where%20you%20can,unique%20sound%20on%20your%20instrument) [\[38\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=press%20shift%20and%20M4%20in,element%2C%20random%2C%20tremolo%20and%20value) [\[39\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=element%20uses%20the%20built,use%20as%20a%20modulation%20source) [\[40\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotating%20the%20mid%20gray%20knob,lfo%20affects%20the%20destination%20parameter) [\[41\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotating%20the%20light%20gray%20knob,to%20assign%20the%20lfo%20to) [\[42\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotating%20or%20pressing%20down%20the,that%20you%20wish%20to%20modulate) [\[43\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=some%20lfos%20feature%20sub%20functions%E2%80%94you,shift%20and%20rotating%20the%20encoders) [\[66\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=settings%2Fmod) [\[67\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=setting) [\[68\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20light%20gray%20or,value%20on%20the%20selected%20setting) [\[69\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=14) [\[70\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=setting) [\[71\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=rotate%20the%20light%20gray%20or,value%20on%20the%20selected%20setting) [\[72\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20create%20your%20own%20tuning%2C,go%20to%20settings%2C%20then%20tuning) [\[73\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20tuning) [\[74\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=edit) [\[75\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=select%20the%20note%20you%20wish,cents) [\[76\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=press%20shift%20and%20any%20track,the%20preset%20on%20that%20track) [\[77\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20copy%20a%20sound%20from,press%20M2%20to%20copy%20it) [\[78\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=to%20paste%20a%20sound%20from,paste%20it%20into%20that%20track) [\[79\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=) [\[80\]](https://teenage.engineering/guides/op-xy/instrument#:~:text=delete%20preset) OP–XY guide: instrument \- teenage engineering

[https://teenage.engineering/guides/op-xy/instrument](https://teenage.engineering/guides/op-xy/instrument)

[\[9\]](https://teenage.engineering/guides/op-xy/sample#:~:text=) [\[10\]](https://teenage.engineering/guides/op-xy/sample#:~:text=rotate%20the%20light%20grey%20knob,level%20on%20the%20vu%20meter) [\[11\]](https://teenage.engineering/guides/op-xy/sample#:~:text=start%20sampling) [\[12\]](https://teenage.engineering/guides/op-xy/sample#:~:text=key%20select) [\[13\]](https://teenage.engineering/guides/op-xy/sample#:~:text=record%20sample) [\[14\]](https://teenage.engineering/guides/op-xy/sample#:~:text=previous%20sample) [\[15\]](https://teenage.engineering/guides/op-xy/sample#:~:text=clear) [\[16\]](https://teenage.engineering/guides/op-xy/sample#:~:text=rotate%20the%20dark%20grey%20knob,the%20selected%20key%20and%20sample) [\[17\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20start) [\[18\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20end) [\[19\]](https://teenage.engineering/guides/op-xy/sample#:~:text=play%20mode) [\[20\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20direction) [\[21\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20fade) [\[22\]](https://teenage.engineering/guides/op-xy/sample#:~:text=sample%20gain) [\[23\]](https://teenage.engineering/guides/op-xy/sample#:~:text=hold%20shift%20and%20click%20the,until%20release%20and%20loop%20off) [\[24\]](https://teenage.engineering/guides/op-xy/sample#:~:text=press%20a%20key%20to%20select,by%20pitching%20those%20samples%20down) [\[25\]](https://teenage.engineering/guides/op-xy/sample#:~:text=,152) OP–XY guide: sample

[https://teenage.engineering/guides/op-xy/sample](https://teenage.engineering/guides/op-xy/sample)

[\[32\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=pitchbend%20as%20a%20modulation) [\[34\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=pitchbend%20as%20a%20modulation) [\[35\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=now%20hold%20shift%20and%20rotate,pitchbend%E2%80%99s%20pitch%20modulation%20to%20off) [\[36\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=ensure%20that%20the%20velocity%20setting,for%20more%20vigorous%20playing) [\[62\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=OP%E2%80%93XY%20supports%20multi,with%20the%20mid%20gray%20knob) [\[63\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=start%20by%20setting%20the%20multi,is%20shown%20on%20the%20screen) [\[64\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=to%20connect%20the%20OP%E2%80%93XY%20to,capable%20device%20firstly%20press%20com) [\[65\]](https://teenage.engineering/guides/op-xy/how-to#:~:text=hold%20shift%20then%20press%20instrument,to%20enter%20the%20preset%20settings) OP–XY guide: how to \- teenage engineering

[https://teenage.engineering/guides/op-xy/how-to](https://teenage.engineering/guides/op-xy/how-to)

[\[44\]](https://teenage.engineering/guides/op-xy/fx#:~:text=change%20fx) [\[45\]](https://teenage.engineering/guides/op-xy/fx#:~:text=you%20can%20then%20use%20the,M1%20to%20confirm%20your%20selection) OP–XY guide: fx \- teenage engineering

[https://teenage.engineering/guides/op-xy/fx](https://teenage.engineering/guides/op-xy/fx)

[\[46\]](https://teenage.engineering/guides/op-xy/mix#:~:text=17) [\[47\]](https://teenage.engineering/guides/op-xy/mix#:~:text=rotate%20the%20dark%20gray%20encoder,bass%20that%20is%20too%20loud) [\[48\]](https://teenage.engineering/guides/op-xy/mix#:~:text=blend) [\[49\]](https://teenage.engineering/guides/op-xy/mix#:~:text=17) [\[50\]](https://teenage.engineering/guides/op-xy/mix#:~:text=press%20M3%20to%20adjust%20the,master%20saturator) [\[51\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,59) [\[52\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,62) [\[53\]](https://teenage.engineering/guides/op-xy/mix#:~:text=blend) [\[54\]](https://teenage.engineering/guides/op-xy/mix#:~:text=17) [\[55\]](https://teenage.engineering/guides/op-xy/mix#:~:text=rotate%20the%20dark%20gray%20encoder,route%20through%20the%20percussion%20group) [\[56\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,74) [\[57\]](https://teenage.engineering/guides/op-xy/mix#:~:text=rotate%20the%20light%20gray%20encoder,and%20build%20a%20heavier%2C%20hard) [\[58\]](https://teenage.engineering/guides/op-xy/mix#:~:text=,80) OP–XY guide: mix \- teenage engineering

[https://teenage.engineering/guides/op-xy/mix](https://teenage.engineering/guides/op-xy/mix)

[\[59\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=punch%E2%80%93in%20fx%20track) [\[60\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=some%20punch%E2%80%93in%20fx%20will%20also,while%20using%20the%20punch%E2%80%93in%20fx) [\[61\]](https://teenage.engineering/guides/op-xy/auxiliary#:~:text=some%20punch%E2%80%93in%20fx%20will%20also,while%20using%20the%20punch%E2%80%93in%20fx) OP–XY guide: auxiliary \- teenage engineering

[https://teenage.engineering/guides/op-xy/auxiliary](https://teenage.engineering/guides/op-xy/auxiliary)