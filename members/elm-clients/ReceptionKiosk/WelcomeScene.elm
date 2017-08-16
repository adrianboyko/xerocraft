
module ReceptionKiosk.WelcomeScene exposing (init, update, view)

-- Standard
import Html exposing (..)

-- Third Party

-- Local
import ReceptionKiosk.Types exposing (..)
import ReceptionKiosk.SceneUtils exposing (..)

-----------------------------------------------------------------------------
-- INIT
-----------------------------------------------------------------------------

init : Flags -> (WelcomeModel, Cmd Msg)
init flags = ({}, Cmd.none)

-----------------------------------------------------------------------------
-- UPDATE
-----------------------------------------------------------------------------

update : WelcomeMsg -> Model -> (WelcomeModel, Cmd Msg)
update msg kioskModel =
  let sceneModel = kioskModel.welcomeModel
  in case msg of

    WelcomeSceneWillAppear ->
      let sceneModel = kioskModel.welcomeModel
      in (sceneModel, send Reset)

-----------------------------------------------------------------------------
-- VIEW
-----------------------------------------------------------------------------

view : Model -> Html Msg
view kioskModel =
  genericScene kioskModel
    "Welcome!"
    "Choose one of the following:"
    (text "")
    [ ButtonSpec "I'm new!" (Push DoYouHaveAcct)
    , ButtonSpec "Check In" (Push CheckIn)
    , ButtonSpec "Check Out" (Push CheckOut)
    ]

