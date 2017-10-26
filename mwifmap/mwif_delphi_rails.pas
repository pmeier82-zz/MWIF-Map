// ****************************************************************************
// No icon in the hex requires more work.
// ****************************************************************************
if not Found then
begin                 // 1st: Avoid all sea hexsides.
  AllSeaCount := 0;

  for HCounter := 0 to 5 do         // For each hexside.
  begin
    Map.AdjacentHex(GivenCol, GivenRow, HCounter, AHex);  // Get Hex adjacent.
    // ****************************************************************************
    // If defined as a coastal hex or if there is an all sea hex adjacent.
    // ****************************************************************************
    if (Map.HexsideTerrain) or
       (Map.Terrain <= teLake) then
    begin
      AllSea := True;       // Hexside is an all sea hexside.
      Inc(AllSeaCount);
      Found := True;
    end
    else AllSea := False;
  end;

  if Found then
  begin
    case AllSeaCount of
    1:
      begin
	for HCounter := 0 to 5 do
	begin    // 0, 1, 2, 3, 4, 5 --> 3, 5, 7, 9, 11, 1
	  if AllSea then
	    TargetPosition := (((HCounter * 2) + 3) mod 12) + 12;
	end;

	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
      end;

    2:
      begin
	SmallS := -1;
	LargeS := 0;      // For the compiler's reassurance

	for HCounter := 0 to 5 do
	begin
	  if AllSea then
	  begin
	    if SmallS < 0 then SmallS := HCounter
	    else LargeS := HCounter;
	  end;
	end;

	if (LargeS - SmallS) = 3 then TargetPosition := 0
	else
	begin   // The formula is strange, but true
	  if (LargeS - SmallS) < 3 then TargetPosition := LargeS + SmallS + 3
	  else TargetPosition := LargeS + SmallS - 3;
	end;

	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
      end;

    3:
      begin
	SmallS := -1;
	MediumS := -1;
	LargeS := 0;      // For the compiler's reassurance

	for HCounter := 0 to 5 do
	begin
	  if AllSea then   // Look for the all sea sides
	  begin
	    if SmallS < 0 then SmallS := HCounter
	    else if MediumS < 0 then MediumS := HCounter
	    else LargeS := HCounter;
	  end;
	end;
	// ****************************************************************************
	// All even or all odd means that none of them are adjacent
	// ****************************************************************************
	if ((SmallS mod 2) = (MediumS mod 2)) and
	  ((SmallS mod 2) = (LargeS mod 2)) then TargetPosition := 0
	else
	begin   // Check if all 3 are adjacent
	  if ((SmallS + MediumS + LargeS) mod 3) = 0 then
	  begin      // All adjacent
	    case (SmallS + LargeS) of
	    2: TargetPosition := 5;
	    4: TargetPosition := 7;
	    6: TargetPosition := 9;
	    8: TargetPosition := 11;
	    5: if MediumS = 4 then TargetPosition := 1
	      else TargetPosition := 3;
	    end;
	  end
	  else    // Neither all adjacent nor all separate
	  begin   // Use the one that is not opposite one of the others
	    if (LargeS - MediumS) = 3 then
	      TargetPosition := ((SmallS * 2) + 3) mod 12
	    else if (LargeS - SmallS) = 3 then
	      TargetPosition := ((MediumS * 2) + 3) mod 12
	    else TargetPosition := ((LargeS * 2) + 3) mod 12;
	  end;
	end;

	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
      end;

    4:
      begin
	SmallS := -1;
	LargeS := 0;      // For the compiler's reassurance

	for HCounter := 0 to 5 do
	begin
	  if not AllSea then   // Look for the non-allsea sides
	  begin
	    if SmallS < 0 then SmallS := HCounter
	    else LargeS := HCounter;
	  end;
	end;

	SmallS := (SmallS + 3) mod 6;   // Take the opposite sides
	LargeS := (LargeS + 3) mod 6;

	if LargeS < SmallS then
	begin                           // Switch small and large
	  HCounter := SmallS;
	  SmallS := LargeS;
	  LargeS := HCounter;
	end;

	if (LargeS - SmallS) = 3 then TargetPosition := 0
	else
	begin   // The formula is strange, but true
	  if (LargeS - SmallS) < 3 then TargetPosition := LargeS + SmallS + 3
	  else TargetPosition := LargeS + SmallS - 3;
	end;

	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
      end;

    5:
      begin
	for HCounter := 0 to 5 do
	begin    // 0, 1, 2, 3, 4, 5 --> 3, 5, 7, 9, 11, 1
	  if not AllSea then
	    TargetPosition := ((HCounter * 2) + 9) mod 12;
	end;

	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
	AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
      end;

    6:     // This should never occur, but it does.
      begin
	TargetPosition := 0;
      end;
    end;
  end    // End of all sea hexsides in hex.
  else
  begin  // 2nd: Count how many rail hexsides there are for the hex.
    RailHexsideCount := 0;
    SmallS := -1;
    MediumS := -1;
    LargeS := 0;      // For the compiler's reassurance.

    for HCounter := 0 to 5 do         // For each hexside.
    begin
      if (Map.HexsideTerrain) or
	(Map.HexsideTerrain) or
	(Map.HexsideTerrain) then
      begin
	RailHexside := True;   // Hexside is a rail hexside.
	Inc(RailHexsideCount);
	if SmallS < 0 then SmallS := HCounter        // 1st hexside found.
	else if MediumS < 0 then MediumS := HCounter // 2nd hexside found.
	else LargeS := HCounter;                     // Last hexside found.
      end
      else RailHexside := False;
    end;

    case RailHexsideCount of
    0: TargetPosition := 0;   // If all else fails, center of the hex

    1:        // 0, 1, 2, 3, 4, 5 --> 21, 23, 13, 15, 17, 19
      TargetPosition := 12 + (((SmallS * 2) + 9) mod 12);

    2:
      begin
	if (MediumS - SmallS) = 3 then TargetPosition := 0
	else if (SmallS > 1) or ((SmallS = 1) and (MediumS = 3)) then
	  TargetPosition := MediumS + SmallS + 9
	else if MediumS < 3 then TargetPosition := MediumS + SmallS + 21
	else TargetPosition := MediumS + SmallS + 15;
      end;

    3:
      begin
	// ****************************************************************************
	// All even or all odd means that none of them are adjacent
	// ****************************************************************************
	if ((SmallS mod 2) = (MediumS mod 2)) and
	  ((SmallS mod 2) = (LargeS mod 2)) then TargetPosition := 0
	else
	begin  // Check if all 3 are adjacent
	  if ((SmallS + MediumS + LargeS) mod 3) = 0 then
	  begin      // All are adjacent
	    case (SmallS + LargeS) of
	    2: TargetPosition := 23;
	    4: TargetPosition := 13;
	    6: TargetPosition := 15;
	    8: TargetPosition := 17;
	    5: if MediumS = 4 then TargetPosition := 19
	      else TargetPosition := 21;
	    end;
	  end
	  else  TargetPosition := 0;   // If all else fails, center of the hex
	end;
      end;

    4:
      begin
	SmallS := -1;
	LargeS := 0;      // For the compiler's reassurance

	for HCounter := 0 to 5 do
	begin
	  if not RailHexside then   // Look for non-rail hexsides
	  begin
	    if SmallS < 0 then SmallS := HCounter
	    else LargeS := HCounter;
	  end;
	end;

	if (SmallS + 2 = LargeS) or (SmallS + 4 = LargeS) then
	begin    // Special case of 3 out of 4 adjacent
	  if (LargeS - SmallS) < 3 then TargetPosition := LargeS + SmallS + 15
	  else TargetPosition := LargeS + SmallS + 9;
	end
	else TargetPosition := 0;   // If all else fails, center of the hex
      end;

    5,6: TargetPosition := 0;   // If all else fails, center of the hex
    end;

    AdjustWeightTarget(Side, TargetPosition, DynamicWeight);
  end;   // End of no all sea hexsides in hex
end;     // End of no label


procedure AdjustWeightTarget(const ThruSide, ClockPosIn: Integer;
			     var AWeight: Integer);
var
  ClockPos: Integer;
 // ****************************************************************************
 // This routine takes a clock position and weights where the rail line crosses
 // the hexside.
 //  SideWeight ranges from 8 (double left) to 12 (double right).
 // ****************************************************************************
begin
  if ClockPosIn = 0 then ClockPos := ClockPosIn
  else ClockPos := Succ((Pred(ClockPosIn) mod 12)); // Convert 13 - 24 to 1 - 12

  case ThruSide of
  0:
    case ClockPos of
    0, 3, 9: ;                       // Straight

    10..12, 1, 2: Inc(AWeight);      // Right

    4..8: Dec(AWeight);              // Left
    end;

  1:
    case ClockPos of
    0, 5, 11: ;                      // Straight

    12, 1..4: Inc(AWeight);          // Right

    6..10: Dec(AWeight);             // Left
    end;

  2:
    case ClockPos of
    0, 1, 7: ;                       // Straight

    2..6: Inc(AWeight);              // Right

    8..12: Dec(AWeight);             // Left
    end;

  3:
    case ClockPos of
    0, 3, 9: ;                       // Straight

    4..8: Inc(AWeight);              // Right

    10..12, 1, 2: Dec(AWeight);      // Left
    end;

  4:
    case ClockPos of
    0, 5, 11: ;                      // Straight

    6..10: Inc(AWeight);             // Right

    12, 1..4: Dec(AWeight);          // Left
    end;

  5:
    case ClockPos of
    0, 1, 7: ;                       // Straight

    8..12: Inc(AWeight);             // Right

    2..6: Dec(AWeight);              // Left
    end;
  end;
end;
